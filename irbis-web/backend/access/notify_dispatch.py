#!/usr/bin/env python3
"""Воркер-диспетч внешней доставки уведомлений (ребро 11.3, движок A6, эпик #188).

Что это
-------
Тонкий *оркестратор* поверх :class:`access.notifications.NotificationQueue.dispatch`.
``notifications.py`` уже несёт очередь, журнал доставки, каналы (Memory/Email/Sms/
InApp) и сам цикл ``dispatch``/``process_once``. Чего там НЕ было — слоя, который
по конфигу тенанта собирает *набор живых каналов*, прогоняет через него осевшую
очередь и отчитывается, какие каналы активны. Этот воркер закрывает именно эту
дыру: он не реализует доставку заново, а связывает «конфиг -> каналы -> dispatch».

Принципы (по ТЗ ребра 11.3)
---------------------------
  * **InApp всегда доступен.** In-app inbox — терминальный, локальный, не требует
    внешнего шлюза/согласия. Он есть в наборе всегда, поэтому диспетч никогда не
    «теряет» уведомление: при выключенных внешних каналах всё садится в inapp.
  * **Внешние каналы по умолчанию OFF.** email/SMS добавляются в набор ТОЛЬКО если
    конфиг тенанта помечает их ``enabled``. Реальной отправки (SMTP/SMS) здесь нет
    — каналы остаются заглушками ``notifications.EmailChannel``/``SmsChannel``,
    конфигурируемыми и выключенными по умолчанию. Нет в наборе -> цепочка канала
    в строке (``email`` сначала, ``inapp`` следом) промахивается по отсутствующему
    каналу и доезжает на inapp (fallback).
  * **Идемпотентность.** ``run_once`` зовёт ``dispatch`` поверх очереди: повторный
    прогон осевшей очереди не порождает новых ``sent`` (нет pending + журнал каналов
    блокирует повторную отправку). Гарантию даёт сама очередь — воркер её сохраняет.
  * **Best-effort, не бросает.** Любая ошибка построения каналов/прогона глотается и
    превращается в нулевую/частичную сводку — фоновый воркер не должен падать.

Конфиг тенанта
--------------
``build_channels(config)`` принимает свободный dict. Распознаются ключи под каналы
в нескольких удобных формах (чтобы не диктовать жёсткую схему конфига):

  * ``{'email': {'enabled': True}, 'sms': {'enabled': False}}`` — вложенный,
  * ``{'email': True}`` / ``{'email': False}`` — короткий булев,
  * ``{'channels': {'email': {...}}}`` — под общим ключом ``channels``.

InApp всегда в наборе и не конфигурируется (его нельзя выключить).
"""
from access import notifications as nt


# --------------------------------------------------------------------------- #
# Конфиг -> набор живых каналов.
# --------------------------------------------------------------------------- #
# Внешние каналы, которые воркер умеет поднимать из конфига. InApp намеренно НЕ
# здесь: он терминальный и добавляется безусловно, его нельзя выключить.
_EXTERNAL_CHANNELS = {
    'email': nt.EmailChannel,
    'sms': nt.SmsChannel,
}


def _channel_config(config, name):
    """Достать под-конфиг канала ``name`` из свободного ``config`` (см. модульный
    docstring о допустимых формах). Возвращает то, что нашлось (dict | bool | None).
    """
    if not isinstance(config, dict):
        return None
    if name in config:
        return config[name]
    nested = config.get('channels')
    if isinstance(nested, dict) and name in nested:
        return nested[name]
    return None


def _is_enabled(channel_config):
    """Помечен ли канал как ``enabled``? По умолчанию OFF.

    Принимает булев (``True``/``False``) или dict с ключом ``enabled``. Что угодно
    непонятное/отсутствующее -> выключен (внешние каналы по умолчанию OFF).
    """
    if channel_config is True:
        return True
    if isinstance(channel_config, dict):
        return bool(channel_config.get('enabled', False))
    return False


def build_channels(config=None):
    """Собрать ``{name: Channel}`` из конфига тенанта.

    * InApp — ВСЕГДА (терминальный fallback, не выключается).
    * email/sms — ТОЛЬКО если конфиг помечает их ``enabled``; иначе их нет в наборе
      (-> цепочка канала в строке промахивается и доезжает на inapp).

    Best-effort: некорректный конфиг или сбой конструктора канала просто пропускают
    канал, оставляя как минимум inapp. Никогда не бросает.
    """
    channels = {'inapp': nt.InAppChannel()}
    try:
        for name, factory in _EXTERNAL_CHANNELS.items():
            cfg = _channel_config(config, name)
            if not _is_enabled(cfg):
                continue
            try:
                # available=True: канал включён конфигом и принимает (заглушка,
                # без реального SMTP/SMS). Выключенный конфигом канала просто нет.
                channels[name] = factory(available=True)
            except Exception:
                # Битый конструктор канала не должен ломать весь набор.
                continue
    except Exception:
        pass  # любой сбой обхода -> остаётся хотя бы inapp
    return channels


# --------------------------------------------------------------------------- #
# Воркер-диспетч.
# --------------------------------------------------------------------------- #
class DispatchWorker:
    """Оркестратор внешней доставки поверх :meth:`NotificationQueue.dispatch`.

    Держит очередь и набор живых каналов; ``run_once`` прогоняет осевшую очередь в
    каналы и возвращает сводку. Внешние каналы конфигурируемы и по умолчанию OFF;
    inapp всегда есть, поэтому диспетч никогда не «теряет» уведомление.

    Параметры:
      * ``queue``    — :class:`NotificationQueue` (источник pending-уведомлений).
      * ``channels`` — готовый ``{name: Channel}`` ИЛИ конфиг тенанта (dict),
        из которого набор соберёт :func:`build_channels`. ``None`` -> только inapp.
      * ``now``      — фиксированные часы для тестов (callable -> float, либо число).
    """

    def __init__(self, queue, channels=None, now=None):
        self.queue = queue
        self.channels = self._resolve_channels(channels)
        self._now = now

    @staticmethod
    def _resolve_channels(channels):
        """Принять либо готовый ``{name: Channel}``, либо конфиг -> собрать набор."""
        if channels is None:
            return build_channels(None)
        # Готовый набор каналов: значения — объекты Channel (есть deliver()).
        if isinstance(channels, dict) and all(
                hasattr(v, 'deliver') for v in channels.values()) and channels:
            # Гарантируем терминальный inapp, если его забыли передать.
            chans = dict(channels)
            chans.setdefault('inapp', nt.InAppChannel())
            return chans
        # Иначе трактуем как конфиг тенанта.
        return build_channels(channels)

    def _clock(self):
        """Текущие часы: callable -> вызвать, число -> как есть, иначе None (now())."""
        n = self._now
        if callable(n):
            try:
                return n()
            except Exception:
                return None
        if isinstance(n, (int, float)):
            return n
        return None

    def run_once(self, limit=100):
        """Прогнать очередь в каналы один раз. Сводка ``{processed,sent,failed,retried}``.

        Зовёт :meth:`NotificationQueue.dispatch` с собранными каналами (dispatch сам
        прокручивает ретраи по backoff в рамках вызова). Идемпотентно: повторный
        прогон осевшей очереди вернёт ``sent==0`` (нет pending; журнал каналов
        блокирует повторную отправку). Best-effort — любая ошибка диспетча
        превращается в нулевую сводку, воркер не падает.
        """
        empty = {'processed': 0, 'sent': 0, 'failed': 0, 'retried': 0}
        try:
            agg = self.queue.dispatch(self.channels, now=self._clock(), limit=limit)
        except Exception:
            return dict(empty)
        # dispatch возвращает агрегат с лишним 'passes' — сводим к контракту воркера.
        return {k: agg.get(k, 0) for k in empty}

    def channel_status(self):
        """Какие каналы активны.

        Возвращает ``{name: bool}`` по всем известным каналам (inapp + внешние):
        ``True`` если канал есть в активном наборе. inapp всегда ``True``.
        """
        known = ['inapp'] + list(_EXTERNAL_CHANNELS.keys())
        status = {name: (name in self.channels) for name in known}
        # На случай нестандартного канала, переданного напрямую в набор.
        for name in self.channels:
            status.setdefault(name, True)
        return status

    def active_channels(self):
        """Имена активных каналов (отсортированы) — удобный хелпер для логов."""
        return sorted(self.channels)
