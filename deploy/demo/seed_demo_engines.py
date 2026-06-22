#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Демо-сид own-store движков связности для публичного демо-стенда Biblio (#226).

Дополняет ``seed_demo_catalog.py`` (тот сеет ~10 одиночных книг для поиска/витрины).
Этот скрипт оживляет НОВЫЕ блоки продукта, которые на демо были пусты, потому что
демо крутится на own-store, а не на разреженном live-ИРБИС:

  • ``/api/linked``     — связи иерархии записей (статьи журнала / тома многотомника).
  • ``/api/fulltext``   — артефакты полного текста (поле 955) + уровень доступа (RIGHT).
  • ``/api/bp/provision`` — книгообеспеченность (Кко/дефицит по связке ВУЗ).

ЧТО ИМЕННО СЕЕТСЯ (всё вымышленное, БЕЗ реальных ПДн):

  1. КАТАЛОГ ДЛЯ linked (own-store CatalogStore, БД=IBIS):
       • журнал «Театральный вестник» (200^a + 11^a ISSN) — несёт HOST=;
       • 3 статьи с 463^c/463^j на него — несут LINK= → /api/linked отдаёт «статьи»;
       • многотомник «Собрание сочинений в трёх томах» (200^a) — HOST=;
       • 3 тома с 481^c на него — LINK= → /api/linked отдаёт «тома».
     Обход делает сам движок: ``catalog.linked_records(db, mfn_журнала, 'children')``.

  2. FULL-TEXT (own-store): RIGHT-шаблон в RightStore + каталожные записи с полем 955:
       • RIGHT-шаблон ``DEMO-FT-RIGHTS``: правила по категориям читателя (50.mnu):
         гость→view, студент→view, преподаватель→download (лимит ^F=50 стр.);
       • 2-3 записи каталога с 955 (^A имя файла, ^N число страниц, ^B=DEMO-FT-RIGHTS).
     Артефакты резолвит ``fulltext.artifacts_for`` ИЗ КАТАЛОЖНОЙ записи (955),
     уровень — ``rights.access_level(категория, db, mfn)`` по 955^B → RightStore.

  3. КНИГООБЕСПЕЧЕННОСТЬ (own-store BookProvisionEngine):
       факультет → специальность → дисциплина + контингент студентов + привязки
       литературы (осн./доп.) к записям каталога по инв. № (910^b), так что
       экземпляры читаются ЖИВЫМИ из own-store-каталога. → ``discipline_provision``
       отдаёт коэффициент Кко и дефицит.

Запускается ВНУТРИ backend-контейнера демо-стенда (как seed_demo_catalog.py),
обычно из seed_demo.sh. Сторы открываются по тем же env-переменным, что и бэкенд
(``core.py``): CATALOG_DB, RIGHT_DB, FULLTEXT_DB (артефакты резолвятся из каталога,
стор пустой), BP_DB. Никакая доменная логика не дублируется — только штатные
движки: ``CatalogStore.save`` / ``RightStore.upsert`` / ``BookProvisionEngine.*``.

ИДЕМПОТЕНТНО: каталожные записи дедуплицируются по заглавию (200^a, поиск T=),
RIGHT-шаблон upsert'ится по id, связка ВУЗ строится идемпотентными add_*/
set_contingent, привязки литературы дедуплицируются по (дисциплина, инв. №, тип).
Повторный прогон не плодит дублей и не падает.
"""
import os
import sys

# Вывод в UTF-8 (внутри контейнера stdout и так UTF-8; на Windows-консоли cp1251
# спотыкается на символах вроде «→»/«•» — переключаем поток на UTF-8, чтобы
# журнал сидинга не падал из-за кодировки).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 — старые Python / нестандартный поток
    pass

# Скрипт лежит в deploy/demo/, бэкенд — в irbis-web/backend/. Внутри контейнера
# бэкенд распакован в /app/backend (WORKDIR). На случай запуска из исходников
# добавляем путь к backend в sys.path.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (
    "/app/backend",  # путь внутри образа (Dockerfile.backend)
    os.path.normpath(os.path.join(_HERE, "..", "..", "irbis-web", "backend")),
):
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from access.catalog import CatalogStore
    from access.rights import RightStore, RightService, CAT_READER_KAT
    from access.fulltext import FulltextRegistry, FulltextStore
    from access.bookprovision import (
        BookProvisionEngine, KIND_MAIN, KIND_EXTRA,
    )
except Exception as exc:  # noqa: BLE001
    sys.stderr.write(
        "ОШИБКА: не удалось импортировать own-store движки (%s).\n"
        "Скрипт рассчитан на запуск ВНУТРИ backend-контейнера демо-стенда.\n" % exc
    )
    raise

# Целевые own-store БД — те же env, что читает бэкенд (core.py). Дефолты совпадают
# с дефолтами core.py (файлы в /data внутри контейнера).
CATALOG_DB = os.environ.get("CATALOG_DB", "/data/catalog.db")
RIGHT_DB = os.environ.get("RIGHT_DB", "/data/right.db")
FULLTEXT_DB = os.environ.get("FULLTEXT_DB", "/data/fulltext.db")
BP_DB = os.environ.get("BP_DB", "/data/bp.db")
# Публичная БД каталога (как в seed_demo_catalog.py и IRBIS_DB_DEFAULT).
DB = os.environ.get("DEMO_CATALOG_DB", os.environ.get("IRBIS_DB_DEFAULT", "IBIS"))

# Категории читателя (коды по 50.mnu — синтетика демо, как в test_rights_lich.py).
KAT_STUDENT = "1"    # студент
KAT_TEACHER = "2"    # преподаватель
KAT_GUEST = "9"      # гость
# id RIGHT-шаблона, на который ссылается 955^B демо-записей с ПТ.
FT_RIGHTS_ID = "DEMO-FT-RIGHTS"


# --------------------------------------------------------------------------- #
# 1. КАТАЛОГ ДЛЯ /api/linked — журнал+статьи (463) и многотомник+тома (481).
#    Хозяин несёт ключ-идентичность под HOST= (200^a / 11^a), зависимая запись —
#    тот же ключ под LINK= (463^c/^j статья→журнал, 481^c том→свод). См.
#    access/catalog.py INDEX_SPEC / linked_records.
# --------------------------------------------------------------------------- #
JOURNAL_TITLE = "Театральный вестник"
JOURNAL_ISSN = "2500-0001"
MULTIVOL_TITLE = "Собрание сочинений в трёх томах"

LINKED_RECORDS = [
    # --- журнал-хозяин (HOST= по 200^a + 11^a ISSN) ---
    {
        "920": "NJ",   # лист ввода «журнал в целом»
        "200": [{"a": JOURNAL_TITLE, "e": "научно-практический журнал"}],
        "11": [{"a": JOURNAL_ISSN}],     # ISSN → HOST=
        "210": [{"a": "Санкт-Петербург", "c": "Демо-Театр-Пресс", "d": "2024"}],
        "101": "rus",
        "610": [{"": "театр"}, {"": "сценическое искусство"}, {"": "журналы"}],
        "910": [{"a": "0", "b": "DEMO-J-0001", "d": "ЧЗ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    # --- 3 статьи журнала (LINK= по 463^c заглавие / 463^j ISSN хозяина) ---
    {
        "920": "ASP",  # аналитическое описание (статья)
        "200": [{"a": "Сценография малых форм", "f": "Е. Е. Сценический"}],
        "700": [{"a": "Сценический", "b": "Е. Е."}],
        "463": [{"c": JOURNAL_TITLE, "j": JOURNAL_ISSN}],  # → журнал
        "101": "rus",
        "610": [{"": "сценография"}, {"": "театр"}],
        "910": [{"a": "0", "b": "DEMO-A-0001", "d": "ЧЗ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        "920": "ASP",
        "200": [{"a": "Режиссёрская партитура спектакля", "f": "Ж. Ж. Постановщик"}],
        "700": [{"a": "Постановщик", "b": "Ж. Ж."}],
        "463": [{"c": JOURNAL_TITLE, "j": JOURNAL_ISSN}],
        "101": "rus",
        "610": [{"": "режиссура"}, {"": "театр"}],
        "910": [{"a": "0", "b": "DEMO-A-0002", "d": "ЧЗ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        "920": "ASP",
        "200": [{"a": "Свет и звук в современном театре", "f": "И. И. Технический"}],
        "700": [{"a": "Технический", "b": "И. И."}],
        "463": [{"c": JOURNAL_TITLE, "j": JOURNAL_ISSN}],
        "101": "rus",
        "610": [{"": "театральная техника"}, {"": "звукорежиссура"}],
        "910": [{"a": "0", "b": "DEMO-A-0003", "d": "ЧЗ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    # --- многотомник-хозяин (сводная запись, HOST= по 200^a) ---
    {
        "920": "PVK",  # сводное описание многотомника
        "200": [{"a": MULTIVOL_TITLE, "f": "К. К. Драматург"}],
        "700": [{"a": "Драматург", "b": "К. К.", "g": "Кузьма Кузьмич"}],
        "210": [{"a": "Москва", "c": "Демо-Издат", "d": "2023"}],
        "101": "rus",
        "610": [{"": "русская драматургия"}, {"": "собрания сочинений"}],
        "910": [{"a": "0", "b": "DEMO-M-0001", "d": "АБ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    # --- 3 тома многотомника (LINK= по 481^c заглавие сводной записи) ---
    {
        "920": "PVK",
        "200": [{"a": "Том 1. Ранние пьесы", "v": "Т. 1", "f": "К. К. Драматург"}],
        "700": [{"a": "Драматург", "b": "К. К."}],
        "481": [{"c": MULTIVOL_TITLE}],   # → сводная запись
        "210": [{"a": "Москва", "c": "Демо-Издат", "d": "2023"}],
        "101": "rus",
        "910": [{"a": "0", "b": "DEMO-V-0001", "d": "АБ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        "920": "PVK",
        "200": [{"a": "Том 2. Зрелая драматургия", "v": "Т. 2", "f": "К. К. Драматург"}],
        "700": [{"a": "Драматург", "b": "К. К."}],
        "481": [{"c": MULTIVOL_TITLE}],
        "210": [{"a": "Москва", "c": "Демо-Издат", "d": "2023"}],
        "101": "rus",
        "910": [{"a": "0", "b": "DEMO-V-0002", "d": "АБ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        "920": "PVK",
        "200": [{"a": "Том 3. Поздние сочинения и письма", "v": "Т. 3",
                 "f": "К. К. Драматург"}],
        "700": [{"a": "Драматург", "b": "К. К."}],
        "481": [{"c": MULTIVOL_TITLE}],
        "210": [{"a": "Москва", "c": "Демо-Издат", "d": "2023"}],
        "101": "rus",
        "910": [{"a": "0", "b": "DEMO-V-0003", "d": "АБ"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
]


# --------------------------------------------------------------------------- #
# 2. FULL-TEXT — каталожные записи с полем 955 (^A файл, ^N страниц, ^B шаблон
#    прав). Артефакты резолвятся из каталожной записи (fulltext.artifacts_for),
#    уровень доступа — по 955^B → RightStore (rights.access_level). 920=VKR/SK —
#    типичные БД-источники с ПТ (диссертации/ВКР/электронные ресурсы).
# --------------------------------------------------------------------------- #
FULLTEXT_RECORDS = [
    {
        "920": "PAZK",
        "200": [{"a": "Электронный практикум по сценической речи", "e": "учебное пособие",
                 "f": "Л. Л. Электронный"}],
        "700": [{"a": "Электронный", "b": "Л. Л."}],
        "210": [{"a": "Санкт-Петербург", "c": "Демо-Театр-Пресс", "d": "2024"}],
        "101": "rus",
        "610": [{"": "сценическая речь"}, {"": "электронные ресурсы"}],
        "675": "792",
        # 955: ^A имя файла ПТ, ^N число страниц, ^B id RIGHT-шаблона.
        "955": [{"a": "demo_scenречь.pdf", "n": "120", "b": FT_RIGHTS_ID}],
        "910": [{"a": "0", "b": "DEMO-FT-0001", "d": "ЭР"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        "920": "PAZK",
        "200": [{"a": "Цифровой архив театральных афиш", "e": "электронное издание",
                 "f": "М. М. Архивный"}],
        "700": [{"a": "Архивный", "b": "М. М."}],
        "210": [{"a": "Санкт-Петербург", "c": "Демо-Театр-Пресс", "d": "2023"}],
        "101": "rus",
        "610": [{"": "театральные афиши"}, {"": "оцифровка"}, {"": "архивы"}],
        "675": "792:004",
        "955": [{"a": "demo_афиши.pdf", "n": "240", "b": FT_RIGHTS_ID}],
        "910": [{"a": "0", "b": "DEMO-FT-0002", "d": "ЭР"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
    {
        # Запись с ПТ, но БЕЗ шаблона прав (955^B пусто) → полный доступ (download)
        # для всех — показывает ветку «пустой шаблон ⇒ download» (rights п.1).
        "920": "PAZK",
        "200": [{"a": "Открытый методический сборник (свободный доступ)",
                 "e": "сборник", "f": "Н. Н. Открытый"}],
        "700": [{"a": "Открытый", "b": "Н. Н."}],
        "210": [{"a": "Москва", "c": "Демо-Издат", "d": "2024"}],
        "101": "rus",
        "610": [{"": "методические материалы"}, {"": "открытый доступ"}],
        "675": "37",
        "955": [{"a": "demo_свободный.pdf", "n": "60"}],   # без ^B
        "910": [{"a": "0", "b": "DEMO-FT-0003", "d": "ЭР"}],
        "907": [{"a": "Демо-каталогизатор"}],
    },
]

# RIGHT-шаблон: правила по категориям читателя (^A=02 категория, 50.mnu).
# Гость→view, студент→view, преподаватель→download(лимит ^F=50 стр.).
# ^C: 0=запрет / 1=постраничный просмотр (view) / 2=скачивание (download).
FT_RIGHTS_RULES = [
    {"category": CAT_READER_KAT, "value": KAT_GUEST, "level": "1"},                 # гость → view
    {"category": CAT_READER_KAT, "value": KAT_STUDENT, "level": "1"},               # студент → view
    {"category": CAT_READER_KAT, "value": KAT_TEACHER, "level": "2", "limit": "50"},  # преподаватель → download(50)
]
FT_RIGHTS_PERIOD = {"start": "20200101", "end": "20301231"}


# --------------------------------------------------------------------------- #
# 3. КНИГООБЕСПЕЧЕННОСТЬ — связка факультет→спец→дисциплина + контингент +
#    привязки литературы к записям каталога по инв. № (910^b). Экземпляры
#    читаются ЖИВЫМИ из own-store-каталога (catalog handle).
# --------------------------------------------------------------------------- #
# Литература привязывается к РЕАЛЬНЫМ записям каталога — берём инв. № (910^b) из
# демо-каталога (seed_demo_catalog.py) + наш многотомник. Так Кко считает
# свободные экземпляры (910^A=0) живьём.
BP_FACULTY = {"code": "ТЕАТР", "name": "Театральный факультет"}
BP_SPECIALTY = {
    "napr": "52.03.05", "spec": "Театроведение",
    "vid": "Бакалавриат", "form": "Очная",
    "name": "Театроведение (бакалавриат, очная)",
}
# Дисциплины: (3^0 id, наименование, семестр, студентов, [привязки литературы]).
# Привязка = (заглавие для отчёта, тип, БД каталога, инв.№ 910^b записи каталога).
BP_DISCIPLINES = [
    {
        "disc_id": "D-001", "name": "История русского театра",
        "semester": "1", "students": 24,
        "bindings": [
            # осн.: две записи демо-каталога (свободные экземпляры → Кко считается)
            ("Война и мир", KIND_MAIN, "DEMO-0001"),
            ("История России с древнейших времён", KIND_MAIN, "DEMO-0009"),
            # доп.: многотомник (свободен) — этот сид завёл DEMO-M-0001
            ("Собрание сочинений в трёх томах", KIND_EXTRA, "DEMO-M-0001"),
        ],
    },
    {
        "disc_id": "D-002", "name": "Основы сценографии",
        "semester": "2", "students": 18,
        "bindings": [
            # осн.: одна запись на 18 студентов → Кко = 1/18 ≈ 0.056 < 0.5 → дефицит
            ("Основы библиотечного дела", KIND_MAIN, "DEMO-0006"),
        ],
    },
]


# --------------------------------------------------------------------------- #
# Утилиты дедупликации.
# --------------------------------------------------------------------------- #
def _title(rec):
    f200 = rec.get("200") or [{}]
    return (f200[0].get("a") or "").strip()


def _find_mfn_by_title(store, db, title):
    """MFN активной записи с заглавием ``title`` (поиск T=), либо None."""
    if not title:
        return None
    try:
        res = store.search(db, "T=%s" % title, limit=1)
    except Exception:  # noqa: BLE001
        return None
    items = (res or {}).get("items") if isinstance(res, dict) else None
    if items:
        return items[0].get("mfn")
    return None


def _save_records(store, records, label):
    """Сохранить список записей идемпотентно (по заглавию). Вернуть {title: mfn}."""
    title_to_mfn = {}
    saved = skipped = failed = 0
    for rec in records:
        title = _title(rec)
        existing = _find_mfn_by_title(store, DB, title)
        if existing is not None:
            title_to_mfn[title] = existing
            skipped += 1
            print("  ~ %s: пропуск (уже есть) mfn=%s: %s" % (label, existing, title))
            continue
        try:
            res = store.save(DB, rec)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("  ! %s: ошибка сохранения %r: %s" % (label, title, exc))
            continue
        if isinstance(res, dict) and res.get("saved"):
            mfn = res.get("mfn")
            title_to_mfn[title] = mfn
            saved += 1
            print("  + %s: mfn=%s: %s" % (label, mfn, title))
        else:
            failed += 1
            print("  ! %s: не сохранено (ФЛК?): %s → %r" % (label, title, res))
    print("  [%s] сохранено=%d пропущено=%d ошибок=%d"
          % (label, saved, skipped, failed))
    return title_to_mfn, (saved, skipped, failed)


# --------------------------------------------------------------------------- #
# Сидеры по блокам.
# --------------------------------------------------------------------------- #
def seed_linked(catalog):
    """Блок 1: журнал+статьи (463) и многотомник+тома (481) для /api/linked."""
    print("\n== Блок 1: каталог для /api/linked (связи иерархии) ==")
    title_to_mfn, _ = _save_records(catalog, LINKED_RECORDS, "linked")

    # Проверка движком: от журнала-хозяина видим статьи, от многотомника — тома.
    jmfn = title_to_mfn.get(JOURNAL_TITLE) or _find_mfn_by_title(
        catalog, DB, JOURNAL_TITLE)
    mmfn = title_to_mfn.get(MULTIVOL_TITLE) or _find_mfn_by_title(
        catalog, DB, MULTIVOL_TITLE)
    articles = catalog.linked_records(DB, jmfn, "children") if jmfn else {"total": 0}
    volumes = catalog.linked_records(DB, mmfn, "children") if mmfn else {"total": 0}
    print("  → журнал mfn=%s: статей (children) = %d" % (jmfn, articles.get("total", 0)))
    for it in articles.get("items", []):
        print("      • [%s] %s" % (it.get("mfn"), it.get("brief")))
    print("  → многотомник mfn=%s: томов (children) = %d"
          % (mmfn, volumes.get("total", 0)))
    for it in volumes.get("items", []):
        print("      • [%s] %s" % (it.get("mfn"), it.get("brief")))
    return {
        "journal_mfn": jmfn, "articles": articles.get("total", 0),
        "multivol_mfn": mmfn, "volumes": volumes.get("total", 0),
    }


def seed_fulltext(catalog, rights_store):
    """Блок 2: RIGHT-шаблон + записи каталога с полем 955 для /api/fulltext."""
    print("\n== Блок 2: full-text (955) + права (RIGHT) для /api/fulltext ==")
    # RIGHT-шаблон (upsert — идемпотентно по id).
    rights_store.upsert(FT_RIGHTS_ID, period=FT_RIGHTS_PERIOD,
                        rules=FT_RIGHTS_RULES,
                        description="Демо-права на ПТ: гость/студент→view, "
                                    "преподаватель→download(50 стр.)")
    print("  + RIGHT-шаблон upsert: id=%s (правил: %d)"
          % (FT_RIGHTS_ID, len(FT_RIGHTS_RULES)))

    # Каталожные записи с 955 (артефакты резолвятся из них).
    title_to_mfn, _ = _save_records(catalog, FULLTEXT_RECORDS, "fulltext")

    # Проверка движками: артефакты + уровень доступа по категориям.
    ft = FulltextRegistry(store=None, catalog=catalog)  # резолв только из каталога
    rights = RightService(store=rights_store, catalog=catalog)
    checks = []
    for rec in FULLTEXT_RECORDS:
        title = _title(rec)
        mfn = title_to_mfn.get(title) or _find_mfn_by_title(catalog, DB, title)
        if mfn is None:
            continue
        arts = ft.artifacts_for(DB, mfn)
        meta955 = [a for a in arts if a.get("kind") == "955"]
        # ВАЖНО: на роуте /api/fulltext категория гостя = None (не код «9»):
        # core._reader_category отдаёт категорию ТОЛЬКО для читательской сессии,
        # для гостя/staff → None. По шаблону с правилами None ни с одним ^B не
        # совпадает → deny (гейтинг ПТ закрыт для анонима). Поэтому реальный
        # «гость» проверяется как None, а не как код категории «9».
        lvl_guest = rights.access_level(None, db=DB, mfn=mfn)
        lvl_student = rights.access_level(KAT_STUDENT, db=DB, mfn=mfn)
        lvl_teacher = rights.access_level(KAT_TEACHER, db=DB, mfn=mfn)
        lim_teacher = rights.page_limit(KAT_TEACHER, db=DB, mfn=mfn)
        pages = meta955[0].get("pages") if meta955 else None
        print("  → '%s' mfn=%s: 955-артефактов=%d, страниц=%s; "
              "доступ гость(None)=%s студент=%s преп=%s (лимит=%s)"
              % (title, mfn, len(meta955), pages,
                 lvl_guest, lvl_student, lvl_teacher, lim_teacher))
        checks.append({
            "mfn": mfn, "artifacts955": len(meta955), "pages": pages,
            "guest": lvl_guest, "student": lvl_student, "teacher": lvl_teacher,
            "teacher_limit": lim_teacher,
        })
    return {"rights_template": FT_RIGHTS_ID, "records": checks}


def _bp_find_disc(bp, specialty_id, disc_id, semester):
    """MFN-аналог: id дисциплины по (спец, disc_id, semester), либо None
    (для дедупликации привязок при повторном прогоне)."""
    for did in bp.list_disciplines(specialty_id):
        row = bp.get_discipline(did)
        if row and str(row.get("disc_id")) == str(disc_id) \
                and str(row.get("semester")) == str(semester):
            return did
    return None


def seed_bookprovision(bp):
    """Блок 3: связка ВУЗ + контингент + привязки литературы для /api/bp/provision."""
    print("\n== Блок 3: книгообеспеченность (связка + Кко) для /api/bp/provision ==")
    fac_id = bp.add_faculty(BP_FACULTY["code"], BP_FACULTY["name"])
    spec_id = bp.add_specialty(
        fac_id, napr=BP_SPECIALTY["napr"], spec=BP_SPECIALTY["spec"],
        vid=BP_SPECIALTY["vid"], form=BP_SPECIALTY["form"],
        name=BP_SPECIALTY["name"])
    print("  + факультет id=%s (%s), специальность id=%s (%s)"
          % (fac_id, BP_FACULTY["code"], spec_id, BP_SPECIALTY["spec"]))

    reports = []
    for d in BP_DISCIPLINES:
        disc_id = bp.add_discipline(
            spec_id, d["disc_id"], name=d["name"], semester=d["semester"],
            students=d["students"], students_source="68z")
        # Привязки литературы — дедупликация: если у дисциплины уже есть привязка
        # на тот же инв. № того же типа, не добавляем повторно.
        existing = bp.list_bindings(disc_id)
        existing_keys = {(b.get("inv_key"), b.get("kind")) for b in existing}
        added = 0
        for title, kind, inv_key in d["bindings"]:
            if (inv_key, kind) in existing_keys:
                continue
            bp.bind_literature(disc_id, title, kind=kind,
                               catalog_db=DB, inv_key=inv_key)
            existing_keys.add((inv_key, kind))
            added += 1
        rep = bp.discipline_provision(disc_id)
        reports.append(rep)
        print("  + дисциплина id=%s «%s» (сем.%s): студентов=%d, привязок=+%d/%d, "
              "Кко=%s, экз.=%d, дефицит=%d, недообеспечена=%s"
              % (disc_id, d["name"], d["semester"], rep["students"], added,
                 len(rep["bindings"]), _fmt(rep["average_kko"]),
                 rep["total_exemplars"], rep["shortfall"],
                 rep["under_provisioned"]))
    # Свод по специальности (кросс-дисциплинарный).
    spec_rep = bp.specialty_provision(spec_id)
    print("  → свод по специальности id=%s: средний Кко=%s, дефицит итого=%d, "
          "недообеспеченных дисциплин=%d"
          % (spec_id, _fmt(spec_rep["average_kko"]), spec_rep["total_shortfall"],
             len(spec_rep["under_provisioned"])))
    return {
        "faculty_id": fac_id, "specialty_id": spec_id,
        "disciplines": [
            {"id": r["discipline_id"], "name": r["name"],
             "students": r["students"], "kko": r["average_kko"],
             "exemplars": r["total_exemplars"], "shortfall": r["shortfall"],
             "under": r["under_provisioned"]}
            for r in reports
        ],
        "specialty_average_kko": spec_rep["average_kko"],
        "specialty_total_shortfall": spec_rep["total_shortfall"],
    }


def _fmt(v):
    return "—" if v is None else ("%.3f" % v)


def main():
    print("Демо-сид own-store движков связности:")
    print("  CATALOG_DB=%s  RIGHT_DB=%s  FULLTEXT_DB=%s  BP_DB=%s  БД=%s"
          % (CATALOG_DB, RIGHT_DB, FULLTEXT_DB, BP_DB, DB))

    catalog = CatalogStore(CATALOG_DB)
    try:
        catalog.ensure_schema()
    except Exception:  # noqa: BLE001
        pass
    rights_store = RightStore(RIGHT_DB)
    bp = BookProvisionEngine(BP_DB, catalog=catalog)

    linked = seed_linked(catalog)
    fulltext = seed_fulltext(catalog, rights_store)
    bookprov = seed_bookprovision(bp)

    print("\n== Итог ==")
    print("  /api/linked:     журнал → %d статей; многотомник → %d томов"
          % (linked["articles"], linked["volumes"]))
    print("  /api/fulltext:   записей с ПТ (955) = %d; RIGHT-шаблон = %s"
          % (len(fulltext["records"]), fulltext["rights_template"]))
    print("  /api/bp/provision: дисциплин = %d; средний Кко по спец. = %s; "
          "дефицит итого = %d"
          % (len(bookprov["disciplines"]),
             _fmt(bookprov["specialty_average_kko"]),
             bookprov["specialty_total_shortfall"]))
    # Минимальная валидация: блоки должны быть НЕ пусты (иначе демо снова мёртвое).
    problems = []
    if linked["articles"] < 1:
        problems.append("нет статей журнала (/api/linked)")
    if linked["volumes"] < 1:
        problems.append("нет томов многотомника (/api/linked)")
    if not fulltext["records"]:
        problems.append("нет записей с ПТ (/api/fulltext)")
    if not bookprov["disciplines"]:
        problems.append("нет дисциплин (/api/bp/provision)")
    if problems:
        sys.stderr.write("ВНИМАНИЕ: блоки не ожили: %s\n" % "; ".join(problems))
        return 1
    print("\nГотово. Новые блоки демо ожили на own-store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
