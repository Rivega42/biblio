#!/usr/bin/env python3
"""Индексатор ИРБИС → CatalogStore (own-индекс поиска, #262).

Назначение
----------
Наполнить НАШ собственный индекс поиска (:class:`access.catalog.CatalogStore`)
записями боевого электронного каталога (EK, ~258k), чтобы /api/search мог
обслуживать одиночные префиксные запросы из own-индекса в обход сломанного
индекса ``K=`` живого ИРБИС (флаг ``OWN_SEARCH_DBS``, см. core.Api.search).

Это разовая/повторяемая ОПЕРАЦИОННАЯ утилита: запускается транзиентно против
БОЕВОГО ИРБИС в режиме ТОЛЬКО-ЧТЕНИЕ (``max_mfn`` + ``read_record``), наполняет
свой стор и завершается. Она НЕ часть обслуживающего приложения и НИЧЕГО не
пишет в ИРБИС.

Чем отличается от ``tools.migrate_irbis``
-----------------------------------------
Мигратор переносит сразу несколько БД (каталог + читателей) в набор сторов и
шифрует ПДн. Индексатор — узкоспециализирован под ОДНУ каталожную базу и под
наполнение CatalogStore, зато несёт операционную обвязку для крупного прогона:

  * БАТЧИ + checkpoint-файл (последний обработанный MFN), ВОЗОБНОВЛЕНИЕ ``--resume``
    после обрыва (~258k записей за один сеанс — реальный риск разрыва соединения);
  * прогресс-лог: % + rec/s + ETA (видно, что прогон жив и когда закончится);
  * идемпотентность: повторный прогон по тем же MFN ПЕРЕЗАПИСЫВАЕТ запись (по
    ключу исходного MFN ``907^_mfn``), не плодит дубли.

Маппинг полей (ИРБИС parser-shape → CatalogStore tag-keyed dict) переиспользуется
из ``tools.migrate_irbis`` (``map_catalog_record``) — он уже сверен и покрыт
тестами (test_migrate.py): repeatable-поля сворачиваются в список инстансов, коды
подполей приводятся к нижнему регистру (канонический ``200^a`` / ``910^b``), поле
без подполей становится «голым» значением. Исходный MFN штампуется в приватное
подполе ``907^_mfn`` как ключ идемпотентности.

Удалённые / пустые / нечитаемые записи пропускаются (как в миграторе). Записи,
отклонённые ФЛК на ``save`` (severity-1), считаются как пропуск отдельной записи,
а не как сбой всего прогона.

CLI
---
::

    py -3.12 -m tools.index_catalog --db EK [--limit N] [--batch 500] \
        [--checkpoint <path>] [--resume]

Подключение к ИРБИС берётся из окружения (``config.Config`` — IRBIS_HOST/PORT/
USER/PASS/WORKSTATION/ENCODING), как у обслуживающего приложения; путь к стору
CatalogStore — из ``CATALOG_DB`` (тот же файл, что читает core.Api). Печатает
итоговый JSON-отчёт ``{db, read, indexed, skipped, errors, from_mfn, to_mfn,
elapsed_sec, rec_per_sec}``.
"""
import argparse
import json
import os
import sys
import time

# Корень backend в sys.path, чтобы `py -3.12 tools/index_catalog.py` и
# `py -3.12 -m tools.index_catalog` работали одинаково (как в доме у тестов).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Переиспользуем СВЕРЕННЫЙ маппинг и детектор удаления из мигратора — НЕ дублируем
# и НЕ правим его (только импорт). map_catalog_record даёт (record, source_mfn) в
# канонической форме CatalogStore + штамп идемпотентности 907^_mfn.
from tools.migrate_irbis import (
    map_catalog_record, _status_is_deleted, SOURCE_MFN_FIELD, SOURCE_MFN_SUB,
)


# --------------------------------------------------------------------------- #
# Источник. Индексатору достаточно утиного интерфейса ``max_mfn(db)`` /
# ``read_record(db, mfn)`` — его удовлетворяет живой ``irbis.SessionManager``
# (через ``config.Config``) И фейковый стаб в тесте (никакого живого сервера).
# --------------------------------------------------------------------------- #
def open_source_from_config(cfg=None):
    """Открыть read-only сессию к ИРБИС по ``config.Config`` (окружение/.env).

    Возвращает ``irbis.SessionManager`` (авто-переподключение, потокобезопасный).
    Импорт ленивый — модуль грузится и на машине без сервера / в юнит-тестах,
    которые подсовывают свой источник."""
    from config import Config
    from irbis import SessionManager
    cfg = cfg or Config()
    return SessionManager(cfg.irbis_host, cfg.irbis_port, cfg.workstation,
                          cfg.irbis_user, cfg.irbis_pass, cfg.timeout,
                          encoding=cfg.irbis_encoding)


def open_catalog_from_config(cfg=None):
    """Открыть CatalogStore по тому же пути (``CATALOG_DB``) и ``AccessStore``, что
    и обслуживающее приложение, с засеянными словарями (чтобы ФЛК словарных правил
    разрешались на ``save``). Импорт ленивый по той же причине."""
    from config import Config
    from access.store import AccessStore
    from access.catalog import CatalogStore
    from access import seed_vocab
    cfg = cfg or Config()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    access = AccessStore(cfg.access_db)
    # Засев словарей идемпотентен и best-effort: на старой схеме без vocab-таблиц
    # не должен валить прогон (ФЛК словарных правил тогда просто no-op).
    try:
        seed_vocab.seed_vocabularies(access, from_catalog=False)
    except Exception:
        pass
    cat_db = os.environ.get('CATALOG_DB', os.path.join(here, 'catalog.db'))
    return CatalogStore(cat_db, access_store=access)


# --------------------------------------------------------------------------- #
# Checkpoint — последний УСПЕШНО обработанный MFN (плоский JSON-файл). Хранит
# {db, last_mfn, updated} и пишется батчами, чтобы ``--resume`` после обрыва
# продолжил с last_mfn+1, а не с начала. Best-effort: повреждённый/чужой
# (по другой БД) чекпойнт игнорируется (старт с нуля), а не валит прогон.
# --------------------------------------------------------------------------- #
def default_checkpoint_path(db):
    """Путь чекпойнта по умолчанию рядом с backend: ``.index_<DB>.checkpoint``."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    safe = ''.join(c for c in (db or '') if c.isalnum() or c in ('_', '-')) or 'DB'
    return os.path.join(here, '.index_%s.checkpoint' % safe.upper())


def read_checkpoint(path, db):
    """Прочитать last_mfn из чекпойнта для БД ``db``; 0, если файла нет / он битый /
    относится к другой БД (тогда возобновлять нечего — начинаем с начала)."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    if str(data.get('db', '')).strip().upper() != str(db).strip().upper():
        return 0          # чекпойнт от другой БД — игнорируем
    try:
        return max(0, int(data.get('last_mfn', 0)))
    except (TypeError, ValueError):
        return 0


def write_checkpoint(path, db, last_mfn):
    """Атомарно записать чекпойнт (через временный файл + os.replace), чтобы обрыв
    в момент записи не оставил полу-записанный JSON. Best-effort: сбой записи
    чекпойнта логируется вызывающим, но не должен валить индексацию."""
    tmp = path + '.tmp'
    payload = {'db': db, 'last_mfn': int(last_mfn), 'updated': time.time()}
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


def clear_checkpoint(path):
    """Удалить чекпойнт по завершении полного прогона (best-effort)."""
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Прогресс. Печатает % + rec/s + ETA в stderr (чтобы итоговый JSON в stdout был
# чистым и парсился). Скорость считается по монотонным часам.
# --------------------------------------------------------------------------- #
def _fmt_eta(seconds):
    """Человекочитаемый ETA ``Чч:Мм:Сс`` (или ``--:--:--`` при неизвестном)."""
    if seconds is None or seconds < 0 or seconds != seconds:   # None / отрицат. / NaN
        return '--:--:--'
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return '%02d:%02d:%02d' % (h, m, s)


def format_progress(done, total, started_at, *, now=None):
    """Строка прогресса: ``[ 12.3%] 1234/10000  18.5 rec/s  ETA 01:02:03``.

    ``done`` — сколько MFN уже пройдено в этом сеансе, ``total`` — сколько
    планируется пройти, ``started_at`` — ``time.monotonic()`` начала. Скорость и
    ETA считаются по фактической скорости сеанса; при нулевой скорости ETA
    неизвестен. Вынесено отдельной чистой функцией, чтобы тест проверял формат без
    реального прогона."""
    now = now if now is not None else time.monotonic()
    elapsed = max(1e-9, now - started_at)
    rate = done / elapsed
    pct = (100.0 * done / total) if total else 100.0
    remaining = (total - done) / rate if (rate > 0 and total) else None
    return '[%5.1f%%] %d/%d  %.1f rec/s  ETA %s' % (
        pct, done, total, rate, _fmt_eta(remaining))


# --------------------------------------------------------------------------- #
# Индексатор.
# --------------------------------------------------------------------------- #
def _new_report(db):
    return {'db': db, 'read': 0, 'indexed': 0, 'skipped': 0, 'errors': 0,
            'from_mfn': None, 'to_mfn': None}


class CatalogIndexer:
    """Прогон индексации ОДНОЙ каталожной БД из ИРБИС в CatalogStore.

    ``source`` должен уметь ``max_mfn(db)`` и ``read_record(db, mfn)`` (живой
    SessionManager удовлетворяет; тест подсовывает фейк). ``catalog`` — целевой
    :class:`access.catalog.CatalogStore`. Прогресс/диагностика идут в ``log``
    (callable(str) или None)."""

    def __init__(self, source, catalog, *, batch=500, checkpoint_path=None,
                 log=None, progress_every=None):
        self.source = source
        self.catalog = catalog
        self.batch = max(1, int(batch))
        self.checkpoint_path = checkpoint_path
        self._log = log
        # Как часто печатать прогресс (по умолчанию — раз в батч).
        self.progress_every = progress_every or self.batch

    def _emit(self, msg):
        if self._log:
            self._log(msg)

    # -- идемпотентность: исходный MFN -> целевой MFN в CatalogStore ---------- #
    def _build_source_index(self, db):
        """Однопроходно построить карту ``{source_mfn: target_mfn}`` из уже
        проиндексированных записей (по штампу ``907^_mfn``).

        Делается ОДИН раз в начале прогона (вместо O(n) скана на каждую запись,
        как в миграторе), поэтому повторный прогон по 258k записям остаётся
        линейным. Включает и логически удалённые целевые записи (их MFN тоже занят
        и должен переиспользоваться при перезаписи)."""
        index = {}
        for mfn in self.catalog.list_mfns(db, include_deleted=True, limit=10 ** 9):
            rec = self.catalog.get(db, mfn, include_deleted=True)
            if rec is None:
                continue
            raw = rec.get(SOURCE_MFN_FIELD)
            for inst in (raw if isinstance(raw, list) else [raw] if raw else []):
                if isinstance(inst, dict) and inst.get(SOURCE_MFN_SUB) is not None:
                    index[str(inst[SOURCE_MFN_SUB])] = mfn
        return index

    def run(self, db, *, limit=None, resume=False, start_mfn=None):
        """Проиндексировать ``db`` из ИРБИС в CatalogStore.

        Обходит MFN от ``start_mfn`` (или 1, или last_mfn+1 чекпойнта при
        ``resume``) до ``max_mfn`` (или ``start+limit-1``). Каждую запись читает,
        приводит к форме CatalogStore (``map_catalog_record``), сохраняет
        ``catalog.save(db, rec, skip_warnings=True)``. Удалённые/пустые/нечитаемые
        и отклонённые ФЛК — пропуск. Чекпойнт пишется после каждого батча и в
        конце; при полном (без ``--limit``) завершении чекпойнт удаляется.

        Возвращает отчёт ``{db, read, indexed, skipped, errors, from_mfn, to_mfn,
        elapsed_sec, rec_per_sec}``."""
        report = _new_report(db)

        # Верхняя граница MFN базы.
        try:
            top = int(self.source.max_mfn(db) or 0)
        except Exception as e:                          # noqa: BLE001 - сервер недоступен
            report['errors'] += 1
            self._emit('max_mfn(%s) failed: %s' % (db, type(e).__name__))
            report['elapsed_sec'] = 0.0
            report['rec_per_sec'] = 0.0
            return report
        if top < 1:
            report['elapsed_sec'] = 0.0
            report['rec_per_sec'] = 0.0
            return report

        # Точка старта: явный start_mfn > чекпойнт (--resume) > 1.
        first = 1
        if start_mfn is not None:
            first = max(1, int(start_mfn))
        elif resume and self.checkpoint_path:
            ckpt = read_checkpoint(self.checkpoint_path, db)
            if ckpt > 0:
                first = ckpt + 1
                self._emit('resume: продолжаю с MFN %d (чекпойнт %d)' % (first, ckpt))

        last = top if limit is None else min(top, first + int(limit) - 1)
        if first > last:
            self._emit('нечего индексировать: first=%d > last=%d' % (first, last))
            report['elapsed_sec'] = 0.0
            report['rec_per_sec'] = 0.0
            return report

        report['from_mfn'] = first
        # Карта идемпотентности (повторный прогон перезаписывает, а не плодит).
        src_index = self._build_source_index(db)

        total = last - first + 1
        started = time.monotonic()
        done = 0
        last_committed = first - 1
        for mfn in range(first, last + 1):
            try:
                parsed = self.source.read_record(db, mfn)
            except Exception:                           # noqa: BLE001 - удалён/заблокирован MFN
                report['skipped'] += 1
            else:
                report['read'] += 1
                if _status_is_deleted(parsed.get('status')) or not parsed.get('fields'):
                    report['skipped'] += 1
                else:
                    self._index_one(db, parsed, src_index, report)
            report['to_mfn'] = mfn
            done += 1
            last_committed = mfn

            # Конец батча: чекпойнт + прогресс.
            if done % self.batch == 0:
                self._checkpoint(db, last_committed, report)
            if done % self.progress_every == 0:
                self._emit(format_progress(done, total, started))

        # Финальный чекпойнт/прогресс (хвост последнего неполного батча).
        self._checkpoint(db, last_committed, report)
        self._emit(format_progress(done, total, started))

        elapsed = max(1e-9, time.monotonic() - started)
        report['elapsed_sec'] = round(elapsed, 3)
        report['rec_per_sec'] = round(done / elapsed, 2)

        # Полный прогон (дошли до max_mfn без --limit) — чекпойнт больше не нужен.
        if self.checkpoint_path and last >= top and limit is None:
            clear_checkpoint(self.checkpoint_path)
        return report

    def _index_one(self, db, parsed, src_index, report):
        """Привести одну разобранную запись к форме CatalogStore и сохранить.

        Идемпотентно: если запись с тем же исходным MFN уже была проиндексирована,
        сохраняем в тот же целевой MFN (перезапись), иначе — новый MFN. Отклонение
        ФЛК (severity-1) считается пропуском отдельной записи, прогон продолжается."""
        record, source_mfn = map_catalog_record(parsed)
        existing_mfn = None
        if source_mfn is not None:
            existing_mfn = src_index.get(str(source_mfn))
        try:
            res = self.catalog.save(db, record, mfn=existing_mfn, skip_warnings=True)
        except Exception as e:                          # noqa: BLE001 - неожиданный сбой стора
            report['errors'] += 1
            self._emit('save mfn %s failed: %s' % (source_mfn, type(e).__name__))
            return
        if not res.get('saved'):
            # ФЛК отклонил запись (severity-1) — пропуск, не сбой прогона.
            report['skipped'] += 1
            return
        report['indexed'] += 1
        # Запомним соответствие, чтобы дубликат исходного MFN В ЭТОМ ЖЕ прогоне
        # тоже перезаписал, а не вставил новый.
        if source_mfn is not None:
            src_index[str(source_mfn)] = res['mfn']

    def _checkpoint(self, db, last_mfn, report):
        """Записать чекпойнт last_mfn (best-effort: сбой логируется, не валит)."""
        if not self.checkpoint_path:
            return
        try:
            write_checkpoint(self.checkpoint_path, db, last_mfn)
        except OSError as e:
            report['errors'] += 1
            self._emit('checkpoint write failed: %s' % e)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def build_arg_parser():
    p = argparse.ArgumentParser(
        prog='index_catalog',
        description='Индексатор ИРБИС → CatalogStore (own-индекс поиска, #262). '
                    'Читает каталожную БД из боевого ИРБИС (read-only) и наполняет '
                    'наш индекс CatalogStore. Подключение к ИРБИС и путь к стору — '
                    'из окружения (config.Config / CATALOG_DB).')
    p.add_argument('--db', required=True,
                   help='код каталожной БД ИРБИС для индексации (напр. EK)')
    p.add_argument('--limit', type=int, default=None,
                   help='ограничить число MFN, обрабатываемых за прогон (smoke / '
                        'поэтапная индексация). По умолчанию — вся база')
    p.add_argument('--batch', type=int, default=500,
                   help='размер батча: после стольких MFN пишется чекпойнт и '
                        'печатается прогресс (по умолчанию 500)')
    p.add_argument('--checkpoint', default=None,
                   help='путь к checkpoint-файлу (по умолчанию '
                        '.index_<DB>.checkpoint рядом с backend)')
    p.add_argument('--resume', action='store_true',
                   help='продолжить с last_mfn+1 из checkpoint-файла (после обрыва)')
    p.add_argument('--start-mfn', type=int, default=None,
                   help='начать с этого MFN (имеет приоритет над --resume)')
    p.add_argument('--quiet', action='store_true',
                   help='не печатать прогресс в stderr (итоговый JSON в stdout всегда)')
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    db = args.db.strip()
    checkpoint = args.checkpoint or default_checkpoint_path(db)
    log = None if args.quiet else (lambda m: print(m, file=sys.stderr, flush=True))

    source = open_source_from_config()
    catalog = open_catalog_from_config()
    indexer = CatalogIndexer(source, catalog, batch=args.batch,
                             checkpoint_path=checkpoint, log=log)
    try:
        report = indexer.run(db, limit=args.limit, resume=args.resume,
                             start_mfn=args.start_mfn)
    finally:
        close = getattr(source, 'close', None)
        if callable(close):
            close()
    report['checkpoint'] = checkpoint
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
