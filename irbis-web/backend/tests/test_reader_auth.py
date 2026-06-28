#!/usr/bin/env python3
"""Тесты двух reader-гэпов под пилот замены jirbis (бэкенд):

  1. Аутентификация читателя С ПАРОЛЕМ (security-critical): билет + пароль,
     сверка с полем пароля записи RDR (130/100), открытый текст ИЛИ несолёный
     MD5; флаг REQUIRE_READER_PASSWORD; неверный пароль -> 401.
  2. «Вы имели в виду» (GET /api/suggest): похожие термины словаря на опечатку,
     ранжирование по близости, публичный доступ (гость), деградация без 500;
     плюс ветка didYouMean в /api/search на пустую выдачу.

Стиль — как tests/test_discovery.py: сконструированный ``Api`` (его конструктор
НЕ подключается к ИРБИС) с маленькой in-memory заглушкой ``FakeIrbis``,
подменяющей ``api.irbis``. Живой ИРБИС-сервер НЕ нужен; sqlite-стор берётся
in-memory (``ACCESS_DB=:memory:``), так что набор полностью зелёный без БД на диске.

Подключён к раннеру tests/test_access.py через generic ``module_checks`` (он
импортирует модуль и зовёт каждый ``*_checks()``, складывая PASS/FAIL), поэтому
тот же CI-шаг, что гоняет test_access.py, гоняет и этот набор без правок .github/.

Отдельно тоже::

    py -3.12 tests/test_reader_auth.py   ->  'ok …' + 'N passed, M failed'
"""
import hashlib
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
# Заглушка ИРБИС: только поверхность, которую трогают auth_reader / suggest.
# Записи в форме irbis.parser.parse_record (dict со списком 'fields').
# --------------------------------------------------------------------------- #
def _fld(tag, value, subfields=None):
    return {'tag': tag, 'value': value, 'text': value, 'subfields': subfields or {}}


class FakeIrbis:
    """In-memory стенд под SessionManager.

    * ``readers``: {ticket: {'fields': [...], 'mfn': N}} — записи RDR по билету.
    * ``terms``: {db: [(count, term), ...]} — словарь для read_terms (отсортирован).
    * ``raise_on``: имена методов, которые должны бросать IrbisError (ветки
      деградации)."""

    def __init__(self, readers=None, terms=None, raise_on=()):
        self._readers = readers or {}
        self._terms = terms or {}
        self.raise_on = set(raise_on)

    def _maybe_raise(self, name):
        if name in self.raise_on:
            from irbis.client import IrbisError
            raise IrbisError(-1, 'stub raise %s' % name)

    def search(self, db, expr, first=1, maxn=0):
        self._maybe_raise('search')
        # Только запросы вида '"RI=<ticket>"' и '"<prefix>=<value>$"' нас интересуют.
        inner = expr.strip().strip('"')
        if inner.startswith('RI='):
            ticket = inner[3:]
            rec = self._readers.get(ticket)
            if rec:
                return 1, [rec['mfn']]
            return 0, []
        # обычный поиск по словарю: считаем «попадание» по точному термину
        for _db, rows in self._terms.items():
            for cnt, term in rows:
                if term == inner.rstrip('$'):
                    return cnt, list(range(1, min(cnt, 5) + 1))
        return 0, []

    def read_record(self, db, mfn):
        self._maybe_raise('read_record')
        for rec in self._readers.values():
            if rec['mfn'] == mfn:
                return {'mfn': mfn, 'status': '0', 'version': '1',
                        'guid': None, 'fields': rec['fields']}
        return {'mfn': mfn, 'status': '0', 'version': '1', 'guid': None, 'fields': []}

    def read_terms(self, db, start, count=20):
        self._maybe_raise('read_terms')
        rows = self._terms.get(db, [])
        out = [(c, t) for (c, t) in rows if t >= start]
        return out[:count]

    def format_record(self, db, mfn, pft='@brief'):
        return ''


def _api(fake, **env):
    """Сконструировать Api (в __init__ нет подключения к ИРБИС) и подменить
    session manager заглушкой. Стор — in-memory sqlite; JWT-секрет фиксирован."""
    os.environ['JWT_SECRET'] = 'reader-auth-test-secret'
    os.environ['ACCESS_DB'] = ':memory:'
    for k, v in env.items():
        os.environ[k] = v
    import core as _core
    importlib.reload(_core)
    api = _core.Api()
    api.irbis = fake
    return api, _core


def _guest(api):
    from access.authz import GUEST_GRANTS
    _tok, sess = api._new_session('guest', 'guest', GUEST_GRANTS, tenant='public')
    return _tok, sess


def _reader_rec(mfn, name='Иванов', pwd_tag=None, pwd_value=None, extra=None):
    fields = [_fld('30', 'RI=', {'RI': str(mfn)}), _fld('10', name)]
    if pwd_tag and pwd_value is not None:
        fields.append(_fld(pwd_tag, pwd_value))
    for f in (extra or []):
        fields.append(f)
    return {'mfn': mfn, 'fields': fields}


# --------------------------------------------------------------------------- #
# Чистые проверки helpers (без Api): пароль + близость терминов.
# --------------------------------------------------------------------------- #
def password_helper_checks():
    print('-- verify_reader_password (helper)')
    import core
    md5 = hashlib.md5('s3cret'.encode('utf-8')).hexdigest()
    check('plaintext верный', core.verify_reader_password('s3cret', 's3cret'))
    check('plaintext неверный', not core.verify_reader_password('nope', 's3cret'))
    check('MD5 верный', core.verify_reader_password('s3cret', md5))
    check('MD5 верный (UPPER hex)', core.verify_reader_password('s3cret', md5.upper()))
    check('MD5 неверный', not core.verify_reader_password('nope', md5))
    # phpass ($P$) перенесённых из jos_users — бесшовный вход (#294, cutover).
    # Реальный дамп jirbis2 (2026-06-28): все 240 учёток несут phpass.
    from access import phpass as _phpass
    ph = _phpass.hash('s3cret')
    check('phpass — это $P$/$H$ длиной 34', _phpass.is_phpass(ph))
    check('phpass верный (бесшовный вход jos_users)',
          core.verify_reader_password('s3cret', ph))
    check('phpass неверный пароль -> False',
          not core.verify_reader_password('nope', ph))
    check('пустой supplied -> False', not core.verify_reader_password('', 's3cret'))
    check('пустой stored -> False', not core.verify_reader_password('x', ''))
    # значение пароля выбирается из 130 (приоритет) либо 100
    r130 = {'fields': [_fld('130', 'aaa'), _fld('100', 'bbb')]}
    r100 = {'fields': [_fld('100', 'bbb')]}
    check('пароль читается из 130 (приоритет)', core._reader_password_value(r130) == 'aaa')
    check('пароль читается из 100 (фолбэк)', core._reader_password_value(r100) == 'bbb')
    check('нет поля пароля -> ""', core._reader_password_value({'fields': []}) == '')


def similarity_helper_checks():
    print('-- term_similarity / levenshtein (helper)')
    import core
    check('равные строки -> 1.0', core.term_similarity('толстой', 'толстой') == 1.0)
    check('одна опечатка близко (>0.6)', core.term_similarity('тлстой', 'толстой') > 0.6)
    check('разные слова далеко (<0.3)', core.term_similarity('тлстой', 'пушкин') < 0.3)
    check('levenshtein одна вставка = 1', core.levenshtein('тлстой', 'толстой') == 1)
    check('levenshtein равные = 0', core.levenshtein('abc', 'abc') == 0)
    # ранжирование: ближайший термин должен идти первым
    cand = ['пушкин', 'толстой', 'тостой']
    ranked = sorted(cand, key=lambda c: -core.term_similarity('тлстой', c))
    check('ранжирование: ближайший первым', ranked[0] in ('толстой', 'тостой'))


# --------------------------------------------------------------------------- #
# Gap 1 — auth_reader: билет + пароль.
# --------------------------------------------------------------------------- #
def auth_reader_password_checks():
    print('-- auth_reader: билет + пароль')
    fake = FakeIrbis(readers={
        '111': _reader_rec(5, name='Иванов', pwd_tag='100', pwd_value='hunter2'),
    })
    api, _core = _api(fake)   # REQUIRE_READER_PASSWORD default = true

    status, payload = api.auth_reader({'ticket': '111', 'password': 'hunter2'})
    check('верный билет+пароль -> 200', status == 200)
    check('200 несёт токен/имя/mfn', payload['ok'] and payload['data'].get('token')
          and payload['data'].get('mfn') == 5)
    check('пароль НЕ возвращается в теле', 'password' not in payload['data'])

    status, payload = api.auth_reader({'ticket': '111', 'password': 'wrong'})
    check('неверный пароль -> 401', status == 401)
    check('401 envelope ok=False', payload['ok'] is False)
    check('401 не раскрывает причину (invalid credentials)',
          payload['error']['message'] == 'invalid credentials')

    status, payload = api.auth_reader({'ticket': '111'})
    check('пропущенный пароль при заданном пароле -> 401', status == 401)

    status, payload = api.auth_reader({'ticket': '999', 'password': 'x'})
    check('несуществующий билет -> 401', status == 401)
    check('несуществующий билет: тот же текст, что неверный пароль',
          payload['error']['message'] == 'invalid credentials')

    status, payload = api.auth_reader({'password': 'x'})
    check('без билета -> 400', status == 400)


def auth_reader_md5_checks():
    print('-- auth_reader: несолёный MD5 в RDR')
    md5 = hashlib.md5('letmein'.encode('utf-8')).hexdigest()
    fake = FakeIrbis(readers={
        '222': _reader_rec(7, pwd_tag='130', pwd_value=md5),   # поле 130 (ИРБИС64+)
    })
    api, _core = _api(fake)
    status, payload = api.auth_reader({'ticket': '222', 'password': 'letmein'})
    check('MD5 в поле 130: верный пароль -> 200', status == 200 and payload['ok'])
    status, payload = api.auth_reader({'ticket': '222', 'password': 'wrong-md5'})
    check('MD5 в поле 130: неверный пароль -> 401', status == 401)


def auth_reader_require_flag_checks():
    print('-- auth_reader: флаг REQUIRE_READER_PASSWORD (читатель без пароля)')
    # читатель БЕЗ поля пароля
    def mk():
        return FakeIrbis(readers={'333': _reader_rec(9, name='Петров')})

    # REQUIRE=true (default): нет пароля у читателя -> 401
    api, _core = _api(mk())
    status, payload = api.auth_reader({'ticket': '333', 'password': ''})
    check('REQUIRE=true + нет пароля -> 401', status == 401)
    check('REQUIRE=true текст "password not set"',
          payload['error']['message'] == 'password not set')

    # REQUIRE=false: legacy — пускаем по билету
    api2, _ = _api(mk(), REQUIRE_READER_PASSWORD='false')
    check('флаг прочитан как false', api2.cfg.require_reader_password is False)
    status, payload = api2.auth_reader({'ticket': '333'})
    check('REQUIRE=false + нет пароля -> 200 (legacy по билету)',
          status == 200 and payload['ok'])

    # даже при REQUIRE=false, если у читателя ЕСТЬ пароль — он проверяется
    api3, _ = _api(FakeIrbis(readers={
        '444': _reader_rec(11, pwd_tag='100', pwd_value='abc')}),
        REQUIRE_READER_PASSWORD='false')
    status, _ = api3.auth_reader({'ticket': '444', 'password': 'abc'})
    check('REQUIRE=false но пароль задан: верный -> 200', status == 200)
    status, _ = api3.auth_reader({'ticket': '444', 'password': 'zzz'})
    check('REQUIRE=false но пароль задан: неверный -> 401', status == 401)


def auth_reader_audit_checks():
    print('-- auth_reader: аудит без утечки пароля')
    fake = FakeIrbis(readers={
        '555': _reader_rec(13, pwd_tag='100', pwd_value='topsecret')})
    api, _core = _api(fake)
    api.auth_reader({'ticket': '555', 'password': 'topsecret'})
    api.auth_reader({'ticket': '555', 'password': 'wrong-guess'})
    rows = api.access.recent_audit()
    check('аудит зафиксировал события auth.reader',
          any(r.get('function') == 'auth.reader' for r in rows))
    blob = repr(rows)
    check('пароль не попал в аудит (plaintext)', 'topsecret' not in blob)
    check('ошибочный ввод не попал в аудит', 'wrong-guess' not in blob)
    results = {r['result'] for r in rows if r.get('function') == 'auth.reader'}
    check('аудит содержит ok и denied', 'ok' in results and 'denied' in results)


# --------------------------------------------------------------------------- #
# Gap 2 — /api/suggest: «Вы имели в виду».
# --------------------------------------------------------------------------- #
def _suggest_terms_fixture():
    return {'IBIS': [
        ('A=ПУШКИН АЛЕКСАНДР', 30),
        ('A=ТОЛСТАЯ ТАТЬЯНА', 4),
        ('A=ТОЛСТОЙ АЛЕКСЕЙ', 12),
        ('A=ТОЛСТОЙ ЛЕВ', 50),
        ('A=ТУРГЕНЕВ ИВАН', 20),
    ]}


def _fake_with_author_terms(raise_on=()):
    # read_terms требует отсортированный по терму список (term >= start).
    terms = {'IBIS': sorted([(c, t) for (t, c) in _suggest_terms_fixture()['IBIS']],
                            key=lambda r: r[1])}
    return FakeIrbis(terms=terms, raise_on=raise_on)


def suggest_checks():
    print('-- /api/suggest')
    api, _core = _api(_fake_with_author_terms())
    _tok, guest = _guest(api)

    # опечатка 'ТОЛСТОЙ' -> 'ТОЛCTOQ' (одна замена): должны прийти Толстые.
    status, payload = api.suggest(guest, 'IBIS', 'A=', 'ТОЛСТОЙ ЛЕВВ')
    check('suggest -> 200', status == 200)
    sug = payload['data']['suggestions']
    check('suggest вернул непустой список на опечатку', len(sug) >= 1)
    check('suggest вернул близкий термин (Толстой Лев первым)',
          sug[0]['value'] == 'ТОЛСТОЙ ЛЕВ')
    check('suggest элемент несёт term/value/count/expr/score',
          all(k in sug[0] for k in ('term', 'value', 'count', 'expr', 'score')))
    check('suggest expr — кавыченный полный термин',
          sug[0]['expr'] == '"A=ТОЛСТОЙ ЛЕВ"')
    check('suggest score в (0,1]', 0 < sug[0]['score'] <= 1.0)
    check('suggest ранжирован по убыванию score',
          all(sug[i]['score'] >= sug[i + 1]['score'] for i in range(len(sug) - 1)))
    check('suggest топ ограничен 8', len(sug) <= 8)
    check('suggest исключил термины другого префикса',
          all(s['term'].startswith('A=') for s in sug))

    # точное совпадение не предлагается как «подсказка»
    status, payload = api.suggest(guest, 'IBIS', 'A=', 'ТОЛСТОЙ ЛЕВ')
    vals = [s['value'] for s in payload['data']['suggestions']]
    check('suggest не включает точный термин сам по себе',
          'ТОЛСТОЙ ЛЕВ' not in vals)

    # пустой q -> пустой список, 200
    status, payload = api.suggest(guest, 'IBIS', 'A=', '')
    check('suggest пустой q -> 200 + []',
          status == 200 and payload['data']['suggestions'] == [])

    # сервер недоступен (read_terms бросает) -> [], не 500
    api2, _ = _api(_fake_with_author_terms(raise_on=('read_terms',)))
    _t2, g2 = _guest(api2)
    status, payload = api2.suggest(g2, 'IBIS', 'A=', 'ТОЛСТОЙ')
    check('suggest деградирует на IrbisError -> 200 + []',
          status == 200 and payload['data']['suggestions'] == [])


def suggest_access_checks():
    print('-- /api/suggest: доступ (публичный, но только публичные БД)')
    api, _core = _api(_fake_with_author_terms())
    _tok, guest = _guest(api)
    # гость вправе звать на публичной базе
    status, _ = api.suggest(guest, 'IBIS', 'A=', 'ТОЛСТОЙ')
    check('гость может звать suggest на публичной БД (200)', status == 200)
    # но не на служебной/ПДн базе (RDR) — public_db_guard -> Denied 403
    denied = False
    try:
        api.suggest(guest, 'RDR', '', 'ИВАНОВ')
    except _core.Denied as d:
        denied = (d.status == 403)
    check('гость НЕ может звать suggest на RDR (403)', denied)
    # нет сессии -> Denied 401
    denied401 = False
    try:
        api.suggest(None, 'IBIS', 'A=', 'x')
    except _core.Denied as d:
        denied401 = (d.status == 401)
    check('без сессии suggest -> 401', denied401)


def suggest_route_checks():
    print('-- route() GET /api/suggest')
    api, _core = _api(_fake_with_author_terms())
    tok, _sess = _guest(api)
    h = {'authorization': 'Bearer ' + tok}
    status, payload = api.route('GET', '/api/suggest',
                                {'db': ['IBIS'], 'prefix': ['A='],
                                 'q': ['ТОЛСТОЙ ЛЕВВ']}, None, h)
    check('route GET /api/suggest -> 200', status == 200)
    check('route suggest вернул подсказки', len(payload['data']['suggestions']) >= 1)
    # без сессии -> 401 через guard
    status, payload = api.route('GET', '/api/suggest',
                                {'db': ['IBIS'], 'q': ['x']}, None, {})
    check('route suggest без сессии -> 401', status == 401)


def did_you_mean_checks():
    print('-- /api/search: didYouMean на пустую выдачу')
    api, _core = _api(_fake_with_author_terms())
    _tok, guest = _guest(api)
    # запрос даёт 0 (опечатка): ждём поле didYouMean
    status, payload = api.search(guest, 'IBIS', '"A=ТОЛСТОЙ ЛЕВВ$"', 1, 20)
    check('search 0 результатов -> 200', status == 200 and payload['data']['total'] == 0)
    check('search добавил didYouMean на опечатку',
          'didYouMean' in payload['data'] and len(payload['data']['didYouMean']) >= 1)
    check('didYouMean содержит близкий вариант',
          'ТОЛСТОЙ ЛЕВ' in payload['data']['didYouMean'])
    # запрос с результатами: didYouMean отсутствует
    status, payload = api.search(guest, 'IBIS', '"A=ТОЛСТОЙ ЛЕВ$"', 1, 20)
    check('search с результатами не добавляет didYouMean',
          'didYouMean' not in payload['data'])
    # сложный булев expr: didYouMean не строится (best-effort, без падения)
    status, payload = api.search(guest, 'IBIS', '"A=ZZZ$" * "T=ZZZ$"', 1, 20)
    check('search сложный expr: 200 без падения', status == 200)
    check('search сложный expr: без didYouMean',
          'didYouMean' not in payload['data'])


def main():
    password_helper_checks()
    similarity_helper_checks()
    auth_reader_password_checks()
    auth_reader_md5_checks()
    auth_reader_require_flag_checks()
    auth_reader_audit_checks()
    suggest_checks()
    suggest_access_checks()
    suggest_route_checks()
    did_you_mean_checks()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    sys.exit(1 if FAIL[0] else 0)


if __name__ == '__main__':
    main()
