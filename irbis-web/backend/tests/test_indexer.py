#!/usr/bin/env python3
"""Тесты индексатора ИРБИС → CatalogStore (own-индекс поиска, #262 —
tools/index_catalog.py).

Гоняют индексатор против ФЕЙКОВОГО источника (синтетические записи, БЕЗ живого
ИРБИС) с наполнением in-memory CatalogStore. Покрыто (контракт задачи):

  1. Индексация N фейковых записей: ``CatalogStore.search`` / ``search_records``
     находят их по T=/A=/K=/IN=; поля/экземпляр сохранены (200^a/700^a/910^b),
     коды подполей канонизированы к нижнему регистру.
  2. Удалённые / пустые / нечитаемые записи пропускаются (считаются), не
     индексируются.
  3. Checkpoint / resume: прервать на середине (через --limit), затем возобновить
     (--resume по чекпойнту) → ВСЕ записи на месте, чекпойнт двигается, по полному
     прогону удаляется.
  4. Идемпотентность: повторный полный прогон НЕ растит число записей (перезапись
     по ключу исходного MFN 907^_mfn), MFN не переминтятся, поиск находит по одной.
  5. Юниты: формат прогресса (% + rec/s + ETA), чтение/запись чекпойнта (в т.ч.
     игнор чужой БД / битого файла).

Файловый чекпойнт пишется во временную директорию (tempfile) и убирается за собой.

Standalone (дом-стиль):
    PYTHONIOENCODING=utf-8 py -3.12 tests/test_indexer.py
        ->  'ok …' + 'N passed, M failed' + код возврата (!=0 при провале).

БЕЗ зависимости от живого сервера и без pytest.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from access.store import AccessStore
from access.catalog import CatalogStore
from access import seed_vocab

from tools.index_catalog import (
    CatalogIndexer, format_progress, _fmt_eta,
    read_checkpoint, write_checkpoint, default_checkpoint_path,
)
from tools.migrate_irbis import SOURCE_MFN_FIELD, SOURCE_MFN_SUB

PASS = [0]
FAIL = [0]


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


# --------------------------------------------------------------------------- #
# FakeIrbis — синтетический источник под интерфейс индексатора (max_mfn /
# read_record). Записи в форме irbis.parser:
#   {'mfn','status','fields':[{'tag','value','text','subfields'}…]}
# Коды подполей в ВЕРХНЕМ регистре (как у живого сервера — маппер их опускает).
# Элемент списка может быть: dict-запись, 'DELETED' (бит удаления в status),
# 'EMPTY' (нет полей) или 'ERROR' (read бросает, как заблокированный/-605 MFN).
# (Образец — tests/test_migrate.py::FakeIrbis / FakeRdrIrbis.)
# --------------------------------------------------------------------------- #
class FakeIrbisError(Exception):
    pass


class FakeIrbis:
    def __init__(self, dbs):
        # dbs: {db: [record-or-sentinel, …]} — 1-индексация по позиции+1.
        self._dbs = dbs

    def max_mfn(self, db):
        return len(self._dbs.get(db, []))

    def read_record(self, db, mfn):
        recs = self._dbs.get(db, [])
        if mfn < 1 or mfn > len(recs):
            raise FakeIrbisError('out of range')
        item = recs[mfn - 1]
        if item == 'ERROR':
            raise FakeIrbisError('-605 locked/deleted')
        if item == 'EMPTY':
            return {'mfn': mfn, 'status': '', 'fields': []}
        if item == 'DELETED':
            return {'mfn': mfn, 'status': '1',
                    'fields': [_fld('200', subs={'A': 'Удалённая'})]}
        return item

    def close(self):
        pass


def _fld(tag, value=None, text='', subs=None):
    """Поле в форме парсера (коды подполей в ВЕРХНЕМ регистре, как у живого)."""
    subs = subs or {}
    if value is None:
        value = ('^' + '^'.join('%s%s' % (k, v) for k, v in subs.items())) if subs else text
    return {'tag': tag, 'value': value, 'text': text, 'subfields': dict(subs)}


def _bib(mfn, title, author=None, inv=None, kw='тест', status=''):
    """Синтетическая каталожная запись EK (форма парсера)."""
    fields = [
        _fld('920', text='PAZK'),
        _fld('200', subs={'A': title, 'F': 'отв. ' + (author or 'N.N.')}),
        _fld('101', text='rus'),
        _fld('907', subs={'A': 'Каталогизатор'}),
        _fld('610', text=kw),
    ]
    if author:
        fields.append(_fld('700', subs={'A': author}))
    if inv:
        fields.append(_fld('910', subs={'A': '0', 'B': inv, 'D': 'ХР'}))
    return {'mfn': mfn, 'status': status, 'fields': fields}


def _catalog():
    """Свежий in-memory CatalogStore с засеянными словарями (чтобы ФЛК словарных
    правил разрешались на save) — как _store() в tests/test_catalog.py."""
    access = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(access, from_catalog=False)
    return CatalogStore(':memory:', access_store=access)


def _many_bibs(n):
    """N валидных каталожных записей с уникальными заглавием/автором/экз.№/ключом.

    Заглавия/авторы — ОДНОТОКЕННЫЕ (без пробелов), потому что собственный
    компаунд-эвалюатор ``search_records`` разбивает выражение по пробелу на
    отдельные термины (мультислово портал шлёт в кавычках). Для индексатора это
    несущественно — он индексирует полное значение поля как термин; нам важно лишь
    findable-поведение, поэтому держим термины односложными и однозначными."""
    return [_bib(i, 'Заглавие-%03d' % i, author='Автор-%03d' % i,
                 inv='INV%05d' % i, kw='kw%03d' % i)
            for i in range(1, n + 1)]


# --------------------------------------------------------------------------- #
# 1. Индексация N записей → findable по T=/A=/K=/IN=; поля/экземпляр сохранены.
# --------------------------------------------------------------------------- #
def index_and_search_checks():
    print('-- индексация N записей + поиск (T=/A=/K=/IN=)')
    src = FakeIrbis({'EK': _many_bibs(10)})
    cat = _catalog()
    rep = CatalogIndexer(src, cat, batch=4).run('EK')

    check('read == 10', rep['read'] == 10)
    check('indexed == 10', rep['indexed'] == 10)
    check('skipped == 0', rep['skipped'] == 0)
    check('errors == 0', rep['errors'] == 0)
    check('from_mfn/to_mfn = 1..10', rep['from_mfn'] == 1 and rep['to_mfn'] == 10)
    check('отчёт несёт elapsed_sec/rec_per_sec',
          'elapsed_sec' in rep and 'rec_per_sec' in rep)
    check('каталог держит 10 активных записей', cat.count('EK') == 10)

    # search / search_records находят по каждому индексируемому префиксу.
    check('search T= находит заглавие', cat.search('EK', 'T=Заглавие-005')['total'] == 1)
    check('search A= находит автора (700^a)', cat.search('EK', 'A=Автор-005')['total'] == 1)
    check('search K= находит ключевое (610)', cat.search('EK', 'K=kw005')['total'] == 1)
    check('search IN= находит экз.№ (910^b)', cat.search('EK', 'IN=INV00005')['total'] == 1)

    sr = cat.search_records('EK', 'T=Заглавие-007')
    check('search_records: total=1', sr['total'] == 1)
    check('search_records: верная запись',
          bool(sr['items']) and sr['items'][0]['record']['200'][0]['a'] == 'Заглавие-007')

    # Поля канонизированы к нижнему регистру подполей; экземпляр на месте.
    rec = cat.get('EK', sr['items'][0]['mfn'])
    check('200^a канонично (нижний регистр кода)', rec['200'][0]['a'] == 'Заглавие-007')
    check('700^a автор сохранён', rec['700'][0]['a'] == 'Автор-007')
    check('910^b инв.№ сохранён', rec['910'][0]['b'] == 'INV00007')
    check('910^a статус экземпляра сохранён', rec['910'][0]['a'] == '0')
    # штамп идемпотентности по исходному MFN.
    stamp = [i for i in rec[SOURCE_MFN_FIELD]
             if isinstance(i, dict) and SOURCE_MFN_SUB in i]
    check('штамп 907^_mfn = исходный MFN (7)',
          bool(stamp) and stamp[0][SOURCE_MFN_SUB] == '7')


# --------------------------------------------------------------------------- #
# 2. Удалённые / пустые / нечитаемые пропускаются (считаются).
# --------------------------------------------------------------------------- #
def skip_checks():
    print('-- пропуск удалённых / пустых / нечитаемых')
    src = FakeIrbis({'EK': [
        _bib(1, 'Хорошая', 'АвторА', 'I1'),
        'DELETED',     # бит удаления в status
        'EMPTY',       # нет полей
        'ERROR',       # read бросает (заблокирован / -605)
        _bib(5, 'ВтораяХорошая', 'АвторБ', 'I2'),
    ]})
    cat = _catalog()
    rep = CatalogIndexer(src, cat, batch=2).run('EK')
    # read: 2 хорошие + удалённая + пустая прочитаны (4); ERROR бросает (не read).
    check('read учитывает прочитанные (4)', rep['read'] == 4)
    check('indexed == 2 (только валидные)', rep['indexed'] == 2)
    check('skipped == 3 (deleted+empty+error)', rep['skipped'] == 3)
    check('каталог держит ровно 2 записи', cat.count('EK') == 2)
    check('удалённая не проиндексирована', cat.search('EK', 'T=Удалённая')['total'] == 0)
    check('валидные на месте',
          cat.search('EK', 'T=Хорошая')['total'] == 1
          and cat.search('EK', 'T=ВтораяХорошая')['total'] == 1)


# --------------------------------------------------------------------------- #
# 3. Checkpoint / resume: прервать на середине → возобновить → всё на месте.
# --------------------------------------------------------------------------- #
def checkpoint_resume_checks():
    print('-- checkpoint / resume (прервать на середине → возобновить)')
    bibs = _many_bibs(10)
    src = FakeIrbis({'EK': bibs})
    cat = _catalog()
    tmpd = tempfile.mkdtemp(prefix='idx_ckpt_')
    ckpt = os.path.join(tmpd, 'ek.checkpoint')
    try:
        # Фаза 1: индексируем только первые 6 (имитация обрыва через --limit).
        rep1 = CatalogIndexer(src, cat, batch=3, checkpoint_path=ckpt).run('EK', limit=6)
        check('фаза1 indexed == 6', rep1['indexed'] == 6)
        check('фаза1 to_mfn == 6', rep1['to_mfn'] == 6)
        check('каталог пока держит 6', cat.count('EK') == 6)
        # чекпойнт указывает на последний обработанный MFN (6) и НЕ удалён (прогон неполный).
        check('чекпойнт-файл существует после неполного прогона', os.path.exists(ckpt))
        check('чекпойнт last_mfn == 6', read_checkpoint(ckpt, 'EK') == 6)

        # Фаза 2: --resume продолжает с MFN 7 до конца.
        rep2 = CatalogIndexer(src, cat, batch=3, checkpoint_path=ckpt).run('EK', resume=True)
        check('фаза2 стартовала с MFN 7', rep2['from_mfn'] == 7)
        check('фаза2 indexed == 4 (7..10)', rep2['indexed'] == 4)
        check('фаза2 to_mfn == 10', rep2['to_mfn'] == 10)

        # ВСЕ 10 на месте, дублей нет.
        check('после resume каталог держит все 10', cat.count('EK') == 10)
        for i in (1, 6, 7, 10):
            check('запись %d findable после resume' % i,
                  cat.search('EK', 'T=Заглавие-%03d' % i)['total'] == 1)
        # полный прогон завершён → чекпойнт убран.
        check('чекпойнт удалён после полного прогона', not os.path.exists(ckpt))
    finally:
        for f in (ckpt, ckpt + '.tmp'):
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(tmpd)


# --------------------------------------------------------------------------- #
# 4. Идемпотентность: повторный прогон не растит число записей.
# --------------------------------------------------------------------------- #
def idempotency_checks():
    print('-- идемпотентность (повтор не плодит дубли)')
    src = FakeIrbis({'EK': _many_bibs(8)})
    cat = _catalog()

    rep1 = CatalogIndexer(src, cat, batch=4).run('EK')
    check('первый прогон indexed == 8', rep1['indexed'] == 8)
    check('каталог держит 8', cat.count('EK') == 8)
    mfns_after_1 = set(cat.list_mfns('EK'))

    # Повторный полный прогон по тем же MFN: перезапись, не дубли.
    rep2 = CatalogIndexer(src, cat, batch=4).run('EK')
    check('повтор read == 8', rep2['read'] == 8)
    check('повтор indexed == 8 (перезапись)', rep2['indexed'] == 8)
    check('каталог ВСЁ ЕЩЁ держит 8 (без дублей)', cat.count('EK') == 8)
    check('повтор не переминтил MFN', set(cat.list_mfns('EK')) == mfns_after_1)
    check('поиск находит ровно по одной',
          cat.search('EK', 'IN=INV00003')['total'] == 1
          and cat.search('EK', 'T=Заглавие-003')['total'] == 1)


# --------------------------------------------------------------------------- #
# 5. Юниты: формат прогресса + чтение/запись чекпойнта.
# --------------------------------------------------------------------------- #
def progress_and_checkpoint_unit_checks():
    print('-- юниты: прогресс (% + rec/s + ETA) + чекпойнт')
    # _fmt_eta: формат Чч:Мм:Сс, неизвестный → плейсхолдер.
    check('_fmt_eta(3661) == 01:01:01', _fmt_eta(3661) == '01:01:01')
    check('_fmt_eta(None) → плейсхолдер', _fmt_eta(None) == '--:--:--')
    check('_fmt_eta(отрицат.) → плейсхолдер', _fmt_eta(-5) == '--:--:--')

    # format_progress: при фикс. started/now скорость и % детерминированы.
    started = 1000.0
    s = format_progress(50, 200, started, now=started + 10.0)   # 5 rec/s, 25%
    check('progress содержит %', '25.0%' in s)
    check('progress содержит rec/s', '5.0 rec/s' in s)
    check('progress содержит счётчик done/total', '50/200' in s)
    # ETA: осталось 150 при 5 rec/s = 30 c → 00:00:30.
    check('progress ETA посчитан', 'ETA 00:00:30' in s)
    # нулевой прогресс → ETA неизвестен, без падения.
    s0 = format_progress(0, 100, started, now=started + 1.0)
    check('progress при done=0 → ETA неизвестен', 'ETA --:--:--' in s0)

    # read/write/clear checkpoint round-trip + защита от чужой БД / битого файла.
    tmpd = tempfile.mkdtemp(prefix='idx_unit_')
    ckpt = os.path.join(tmpd, 'c.checkpoint')
    try:
        check('нет файла → read_checkpoint = 0', read_checkpoint(ckpt, 'EK') == 0)
        write_checkpoint(ckpt, 'EK', 1234)
        check('round-trip last_mfn', read_checkpoint(ckpt, 'EK') == 1234)
        check('чекпойнт другой БД игнорируется (0)', read_checkpoint(ckpt, 'IBIS') == 0)
        # битый файл → 0 (а не исключение).
        with open(ckpt, 'w', encoding='utf-8') as f:
            f.write('{не json')
        check('битый чекпойнт → 0', read_checkpoint(ckpt, 'EK') == 0)
        # атомарная запись не оставляет .tmp.
        write_checkpoint(ckpt, 'EK', 7)
        check('после записи нет .tmp', not os.path.exists(ckpt + '.tmp'))
    finally:
        for f in (ckpt, ckpt + '.tmp'):
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(tmpd)

    # default_checkpoint_path: имя несёт код БД, верхний регистр.
    p = default_checkpoint_path('ek')
    check('default_checkpoint_path несёт код БД', 'EK' in os.path.basename(p))


# --------------------------------------------------------------------------- #
# 6. start_mfn / max_mfn-сбой — поведенческие края.
# --------------------------------------------------------------------------- #
def edge_checks():
    print('-- края: start_mfn, пустая БД, сбой max_mfn')
    # start_mfn имеет приоритет: индексируем только хвост.
    src = FakeIrbis({'EK': _many_bibs(10)})
    cat = _catalog()
    rep = CatalogIndexer(src, cat).run('EK', start_mfn=8)
    check('start_mfn=8 → from_mfn 8', rep['from_mfn'] == 8)
    check('start_mfn=8 → indexed 3 (8..10)', rep['indexed'] == 3)
    check('каталог держит 3', cat.count('EK') == 3)

    # Пустая БД (max_mfn=0) → нечего делать, без падения.
    rep0 = CatalogIndexer(FakeIrbis({'EK': []}), _catalog()).run('EK')
    check('пустая БД → indexed 0, errors 0', rep0['indexed'] == 0 and rep0['errors'] == 0)

    # Сбой max_mfn → errors++, не падение.
    class BoomSource:
        def max_mfn(self, db):
            raise RuntimeError('boom')

        def read_record(self, db, mfn):
            raise RuntimeError('boom')

    repb = CatalogIndexer(BoomSource(), _catalog()).run('EK')
    check('сбой max_mfn → errors >= 1, indexed 0',
          repb['errors'] >= 1 and repb['indexed'] == 0)


def main():
    index_and_search_checks()
    skip_checks()
    checkpoint_resume_checks()
    idempotency_checks()
    progress_and_checkpoint_unit_checks()
    edge_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
