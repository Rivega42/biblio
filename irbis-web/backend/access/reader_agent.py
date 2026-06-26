#!/usr/bin/env python3
"""Reader Agent — тонкий оркестратор НАСТОЛЬНОГО RFID-считывателя (#272).

Настольный считыватель у стойки книговыдачи / станции самообслуживания умеет
ровно четыре вещи (DEVICE_CONTROL_MAP.md §1, TAG_DATA_MODEL.md §6):
  1. прочитать UID метки (ISO 15693, ``ISO15693_GetSystemInfo``);
  2. прочитать/декодировать данные метки → первичный идентификатор экземпляра
     (Primary Item Identifier, relative-OID **1** ISO 28560-2 = инв./штрихкод,
     ключ выдачи в ИРБИС);
  3. запрограммировать чистую метку (закодировать код книги, ``WriteBlock``);
  4. переключить EAS-бит (Electronic Article Surveillance, противокражная
     подпись, NXP ICODE SLIX EnableEAS/DisableEAS).

Сервис — чистый и юнит-тестируемый: железо и кодек спрятаны за ИНЪЕКТИРУЕМЫМИ
СИДАМИ (домовый идиом, ср. ``access/readers.py`` ``rdr_lookup=`` и
``access/locker.py`` ``circulation=``/``devices=``). НЕТ жёстких импортов
кодека/сокетов/БД; конструктор берёт опц. ``transport``/``codec``/``now``.

Сиды (duck-typing, ничего не импортируем):
  * ``transport`` — аппаратный канал:
      - ``read_uid() -> str | None``      — UID метки (hex) или None, если метки нет;
      - ``read_block() -> bytes | None``  — сырые байты user-memory или None;
      - ``write_block(data: bytes) -> bool`` — записать блок, True при успехе;
      - ``set_eas(on: bool) -> bool``     — выставить/снять EAS-бит, True при успехе.
    ``transport is None`` ⇒ «считыватель не подключён»: операции не падают, а
    возвращают понятный результат (``{'uid': None, ...}`` / ``{'ok': False}``).
  * ``codec`` — кодек ISO 28560-2 (модуль ``access.tag_codec`` другого агента;
    СЮДА НЕ ИМПОРТИРУЕМ — только зовём сид):
      - ``decode_block(bytes) -> dict``   — {relative-OID: значение}, OID 1 = itemId;
      - ``encode_block(dict) -> bytes``   — обратно в байты для записи.

Соглашение по EAS (противокражка), DEVICE_CONTROL_MAP.md §5 / TAG_DATA_MODEL.md §5:
  EAS **ВКЛ** = метка защищена (книга «в библиотеке»); ворота поднимают тревогу,
  если защищённая метка покидает зону. EAS **ВЫКЛ** = метка обесточена для
  выноса (книга на руках). Отсюда направление:
      выдача  (issue)  → EAS OFF  (книга может покинуть зону);
      возврат (return) → EAS ON   (книга снова под защитой).
  Тонкие хелперы ``issue_prepare`` / ``return_prepare`` фиксируют это направление.
"""


class ReaderAgentError(Exception):
    """Ошибка некорректного программного использования (а НЕ «нет железа»).

    «Нет считывателя»/«не прочиталось» — это нормальные рантайм-исходы, для них
    операции возвращают dict и не бросают. Исключение — лишь для явно неверного
    вызова (напр. ``program_tag`` с пустым item_id).
    """


# Первичный идентификатор экземпляра — relative-OID 1 (ISO 28560-2, см.
# TAG_DATA_MODEL.md §4: Primary Item Identifier = штрихкод/инв.номер).
PRIMARY_ITEM_OID = 1


class ReaderAgentService:
    """Оркестратор настольного RFID-считывателя поверх инъектируемых сидов.

    Каждая операция возвращает простой dict и НЕ бросает на «нет железа».
    """

    def __init__(self, transport=None, codec=None, now=None):
        self.transport = transport
        self.codec = codec
        # ``now`` — сид часов (как в locker.py), на будущее для меток времени;
        # держим, чтобы сервис оставался чистым и тестируемым.
        import time
        self._now = now or time.time

    # -- чтение метки ------------------------------------------------------- #
    def read_tag(self):
        """Прочитать метку: UID + декодированные данные + первичный itemId.

        Возвращает ``{'uid': str, 'itemId': str|None, 'data': dict}`` при наличии
        метки; ``{'uid': None}`` если метки/считывателя нет.
        """
        if self.transport is None:
            return {'uid': None, 'itemId': None, 'data': {}, 'reason': 'no-reader'}
        uid = self.transport.read_uid()
        if not uid:
            return {'uid': None, 'itemId': None, 'data': {}}
        data = {}
        item_id = None
        raw = self.transport.read_block()
        if raw is not None and self.codec is not None:
            decoded = self.codec.decode_block(raw)
            if isinstance(decoded, dict):
                data = decoded
                item_id = self._primary_item(decoded)
        return {'uid': uid, 'itemId': item_id, 'data': data}

    # -- программирование метки --------------------------------------------- #
    def program_tag(self, item_id, extra=None):
        """Записать на чистую метку код книги (OID 1) + опц. доп. поля.

        ``codec.encode_block({1: item_id, **extra})`` → ``transport.write_block``.
        Пустой ``item_id`` — это ошибка вызова (``ReaderAgentError``).
        Возвращает ``{'ok': bool, 'written': int}`` (written = длина записанных байт).
        """
        if not item_id:
            raise ReaderAgentError('program_tag: empty item_id')
        if self.transport is None:
            return {'ok': False, 'written': 0, 'reason': 'no-reader'}
        if self.codec is None:
            return {'ok': False, 'written': 0, 'reason': 'no-codec'}
        payload = {PRIMARY_ITEM_OID: item_id}
        if extra:
            payload.update(extra)
        data = self.codec.encode_block(payload)
        ok = bool(self.transport.write_block(data))
        return {'ok': ok, 'written': len(data) if ok else 0}

    # -- EAS (противокражка) ------------------------------------------------ #
    def set_security(self, on):
        """Выставить (``on=True``) / снять (``on=False``) EAS-бит метки.

        EAS ON = защищена (в библиотеке), OFF = можно выносить (на руках).
        Возвращает ``{'ok': bool, 'eas': bool}``.
        """
        on = bool(on)
        if self.transport is None:
            return {'ok': False, 'eas': on, 'reason': 'no-reader'}
        ok = bool(self.transport.set_eas(on))
        return {'ok': ok, 'eas': on}

    def issue_prepare(self, item_id):
        """Подготовка к выдаче: снять EAS (книга может покинуть зону) → EAS OFF."""
        return self.set_security(False)

    def return_prepare(self, item_id):
        """Подготовка к возврату: взвести EAS (книга снова под защитой) → EAS ON."""
        return self.set_security(True)

    # -- внутреннее --------------------------------------------------------- #
    @staticmethod
    def _primary_item(decoded):
        """Достать первичный идентификатор (OID 1) из декодированных данных.

        Кодек может класть ключ как int 1 или строку '1' — учитываем оба.
        """
        if PRIMARY_ITEM_OID in decoded:
            val = decoded[PRIMARY_ITEM_OID]
        elif str(PRIMARY_ITEM_OID) in decoded:
            val = decoded[str(PRIMARY_ITEM_OID)]
        else:
            return None
        return None if val is None else str(val)
