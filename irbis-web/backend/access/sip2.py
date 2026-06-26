#!/usr/bin/env python3
"""SIP2 (Standard Interchange Protocol v2) — кодек + ACS-сервис для Biblio.

Стандартные киоски самообслуживания и RFID-станции «умеют» SIP2 (3M SIP2,
v2.00): терминал (SC, self-check) шлёт запросы, библиотечная система (ACS)
отвечает. Чтобы такие устройства могли водить книговыдачу через Biblio, нам
нужен SIP2-сервер (ACS), эмулирующий поднабор протокола. Здесь — чистый кодек
кадра и доменный сервис-диспетчер; сетевой сокет (TCP, терминатор ``\\r``) —
дело слоя транспорта, как и в остальных доменах.

Источник истины — ``docs/devices/EASYBOOKABIS_SIP2_MAP.md`` (построчный разбор
SIP2-клиента надстройки EasyBookAbis). Реализуем пары сообщений из §4 этого
разбора: 93/94 Login, 99/98 SC↔ACS Status, 63/64 Patron Information,
17/18 Item Information, 11/12 Checkout, 09/10 Checkin, 29/30 Renew,
35/36 End Patron Session.

Кадр (§1 разбора):
  ``<MSG><фикс.поля><|XXvalue|…>[AY<seq>AZ<CRC>]\\r``
  * ``MSG`` — 2 цифры id сообщения;
  * фиксированные поля — позиционные, без разделителя;
  * переменные поля — каждое ``XX`` (2 символа кода) + значение + ``|``;
  * опц. конверт ``AY<seq>AZ<CRC>``: ``seq`` 0..9, ``CRC`` — 4 hex-цифры,
    ``CRC = (0x10000 - сумма_байтов) & 0xFFFF`` по всем байтам вплоть до ``AZ``.

Дата/время SIP2: ``YYYYMMDD    HHMMSS`` (4 пробела в зоне таймзоны), как в
``DateConverter.DateToSipFormat`` разбора.

Сидовые контракты (всё duck-typed, как device-адаптер; любой сид ``None`` —
сервис всё равно отдаёт корректный кадр SIP2, без падения):
  * ``circulation``:
      - ``checkout(ticket, item) -> Decision(.ok,.reasons) | bool | None``
      - ``checkin(ticket, item)  -> Decision | bool | None``
      - ``renew(ticket, item)    -> Decision | bool | None``
      - ``loans(ticket)          -> [item_code, …]``
      - ``doc_state(item)        -> str | None`` (SIP2 CirculationStatus, напр. '03')
  * ``readers``:
      - ``find_by_card(code) -> {'abis_code': билет, …} | None``
  * ``devices`` — опц. (резерв для аудита/привязки станции; не обязателен).

Только stdlib, без сети и pip-зависимостей — в точности как ``access/readers.py``.
"""
import time

# --------------------------------------------------------------------------- #
# Идентификаторы сообщений (request id -> response id).
# --------------------------------------------------------------------------- #
MSG_LOGIN = '93'           # -> 94
MSG_LOGIN_RESP = '94'
MSG_SC_STATUS = '99'       # -> 98
MSG_ACS_STATUS = '98'
MSG_PATRON_INFO = '63'     # -> 64
MSG_PATRON_RESP = '64'
MSG_ITEM_INFO = '17'       # -> 18
MSG_ITEM_RESP = '18'
MSG_CHECKOUT = '11'        # -> 12
MSG_CHECKOUT_RESP = '12'
MSG_CHECKIN = '09'         # -> 10
MSG_CHECKIN_RESP = '10'
MSG_RENEW = '29'           # -> 30
MSG_RENEW_RESP = '30'
MSG_END_SESSION = '35'     # -> 36
MSG_END_SESSION_RESP = '36'

# CirculationStatus по умолчанию для неизвестного экземпляра (Other=01 SIP2).
# Доступен='03' (Available). Маппинг статусов — §2.4 разбора.
ITEM_STATUS_UNKNOWN = '01'
ITEM_STATUS_AVAILABLE = '03'


class Sip2Error(Exception):
    """Доменная ошибка SIP2: слишком короткий/битый кадр и т.п."""


# --------------------------------------------------------------------------- #
# Кодек кадра SIP2.
# --------------------------------------------------------------------------- #
class Sip2Codec:
    """Кодек кадра SIP2: контрольная сумма, разбор и сборка.

    Без состояния — все методы статические; экземпляр держать не обязательно.
    """

    DELIM = '|'
    SEQ_CODE = 'AY'
    CRC_CODE = 'AZ'

    # Длины блока фиксированных полей по id сообщения (SIP2 v2.00, дата=18).
    # Нужны парсеру: переменные поля не отделены разделителем от фикс.части, а
    # фикс.поля могут содержать заглавные буквы (Y/N/U…), неотличимые от кодов
    # переменных полей, — поэтому границу fixed/var берём строго по таблице.
    # Для неизвестного id — эвристика (_find_first_code). Значения — суммарная
    # длина позиционных полей до первого переменного (EASYBOOKABIS_SIP2_MAP §2;
    # дата SIP2 ``YYYYMMDD    HHMMSS`` = 18 символов).
    _DT = 18
    FIXED_LEN = {
        '09': 1 + _DT + _DT,        # no_block(1) + xact_date + return_date
        '10': 1 + 1 + 1 + 1 + _DT,  # ok+resensitize+media+alert + xact_date
        '11': 1 + 1 + _DT + _DT,    # renewal_ok+no_block + xact_date + due
        '12': 1 + 1 + 1 + 1 + _DT,  # ok+renewal_ok+media+desensitize + xact_date
        '17': _DT,                  # xact_date
        '18': 2 + 2 + 2 + _DT,      # circ_status+sec_marker+fee_type + xact_date
        '29': 1 + 1 + _DT + _DT,    # renewal_ok+no_block + xact_date + due
        '30': 1 + 1 + 1 + 1 + _DT,  # ok+renewal_ok+media+desensitize + xact_date
        '35': _DT,                  # xact_date
        '36': 1 + _DT,              # end_session ok + xact_date
        '63': 3 + _DT + 10,         # язык(3) + xact_date + summary(10)
        '64': 14 + 3 + _DT,         # patron_status(14) + язык(3) + xact_date
        '93': 2,                    # UID/PWD алгоритмы
        '94': 1,                    # ok
        '98': 7 + 3 + 3 + _DT + 4,  # online+статусы(7) + timeout(3)+retries(3) + дата + версия
        '99': 1 + 3 + 4,            # status(1) + max_print_width(3) + version(4)
    }

    @staticmethod
    def checksum(s):
        """4-hex контрольная сумма SIP2 по строке ``s`` (вплоть до ``AZ``).

        ``CRC = (0x10000 - сумма_байтов(s)) & 0xFFFF`` в верхнем 4-hex
        (``CheckSum.CheckSumAdd`` разбора). Вызывающий передаёт строку,
        ОКАНЧИВАЮЩУЮСЯ на ``AZ`` (маркер уже включён).
        """
        total = sum(ord(c) for c in s) & 0xFFFF
        return '%04X' % ((0x10000 - total) & 0xFFFF)

    @classmethod
    def parse(cls, line):
        """Разобрать кадр SIP2 в dict.

        Возвращает ``{'id', 'fixed', 'fields', 'seq', 'checksum_ok'}``:
          * ``id``          — 2-символьный id сообщения;
          * ``fixed``       — строка фиксированных полей (до первого ``|``,
                              без хвостового ``AY…AZ…`` конверта);
          * ``fields``      — ``{code: value}``; при повторе кода значение
                              становится списком (порядок сохранён);
          * ``seq``         — int 0..9 из ``AY`` или None;
          * ``checksum_ok`` — True/False если есть ``AZ`` (сверка пересчётом),
                              иначе None.

        Бросает :class:`Sip2Error` на слишком короткий/битый кадр.
        """
        if line is None:
            raise Sip2Error('empty SIP2 frame')
        # Терминатор \r/\n — необязателен для разбора.
        raw = line.rstrip('\r\n')
        if len(raw) < 2 or not raw[:2].isdigit():
            raise Sip2Error('SIP2 frame too short / no message id: %r' % (line,))
        msg_id = raw[:2]
        body = raw[2:]

        seq = None
        checksum_ok = None
        # Конверт AY<seq>AZ<CRC> — только если присутствует маркер AZ.
        az = cls.CRC_CODE
        ay = cls.SEQ_CODE
        idx_az = body.rfind(az)
        if idx_az != -1 and len(body) - idx_az >= len(az) + 4:
            crc_given = body[idx_az + len(az):idx_az + len(az) + 4]
            # Хвост после CRC (если был \r — уже срезан); допускаем пустой.
            tail = body[idx_az + len(az) + 4:]
            if all(ch in '0123456789ABCDEFabcdef' for ch in crc_given) and tail == '':
                # Пересчёт суммы по всем байтам кадра вплоть до AZ включительно.
                upto = raw[:len(msg_id) + idx_az + len(az)]
                checksum_ok = (crc_given.upper() == cls.checksum(upto))
                # Вырезаем AY<seq>AZ<CRC> из тела перед разбором полей.
                env_start = idx_az
                # seq — ищем AY непосредственно перед AZ.
                idx_ay = body.rfind(ay, 0, idx_az)
                if idx_ay != -1 and idx_ay >= idx_az - 4:
                    seq_str = body[idx_ay + len(ay):idx_az].rstrip(cls.DELIM)
                    if seq_str.isdigit():
                        seq = int(seq_str)
                        env_start = idx_ay
                body = body[:env_start].rstrip(cls.DELIM)
        else:
            # Нет AZ, но возможен голый AY<seq> в хвосте (без CRC).
            idx_ay = body.rfind(ay)
            if idx_ay != -1:
                seq_str = body[idx_ay + len(ay):].rstrip(cls.DELIM)
                if seq_str.isdigit() and len(seq_str) <= 1:
                    seq = int(seq_str)
                    body = body[:idx_ay].rstrip(cls.DELIM)

        # Фиксированные поля — по таблице длин для типа; дальше — переменные.
        fixed, fields = cls._split_fields(msg_id, body)
        return {
            'id': msg_id,
            'fixed': fixed,
            'fields': fields,
            'seq': seq,
            'checksum_ok': checksum_ok,
        }

    @classmethod
    def _split_fields(cls, msg_id, body):
        """Разделить тело на фиксированную часть и переменные поля.

        Кадр SIP2: ``<fixed><C0><v0>|<C1><v1>|…|`` — каждое переменное поле
        ``CC`` (2 символа кода) + значение, ЗАКАНЧИВАЕТСЯ ``|``. Граница
        fixed/переменные берётся по таблице :data:`FIXED_LEN` (длины фикс.полей
        зависят от типа сообщения; сами фикс.поля могут содержать заглавные
        буквы, неотличимые от кодов). Для неизвестного id — эвристика по первому
        2-буквенному коду.
        """
        fields = {}
        flen = cls.FIXED_LEN.get(msg_id)
        if flen is None:
            flen = cls._guess_fixed_len(body)
        fixed = body[:flen]
        var = body[flen:]
        for seg in var.split(cls.DELIM):
            if seg == '':
                continue
            if len(seg) >= 2:
                cls._put(fields, seg[:2], seg[2:])
            else:
                cls._put(fields, seg, '')
        return fixed, fields

    @staticmethod
    def _guess_fixed_len(body):
        """Длина фикс.части для неизвестного типа: до первого 2-буквенного кода.

        Фикс.поля SIP2 — цифры/пробелы/даты; коды переменных полей — две
        заглавные латинские буквы. Возвращаем индекс первого такого кода (0 —
        если переменные поля начинаются сразу).
        """
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if 'A' <= a <= 'Z' and 'A' <= b <= 'Z':
                return i
        return len(body)

    @staticmethod
    def _put(fields, code, value):
        """Положить поле; при повторе кода — превратить в список."""
        if code in fields:
            cur = fields[code]
            if isinstance(cur, list):
                cur.append(value)
            else:
                fields[code] = [cur, value]
        else:
            fields[code] = value

    @classmethod
    def build(cls, msg_id, fixed='', fields=None, seq=None):
        """Собрать кадр SIP2.

        ``fields`` — список ``[(code, value), …]`` (порядок сохраняется) или
        dict ``{code: value}``. Если ``seq`` не None — дописываем конверт
        ``AY<seq>AZ<CRC>`` и терминатор ``\\r``.
        """
        if fields is None:
            fields = []
        items = fields.items() if isinstance(fields, dict) else fields
        out = [str(msg_id), fixed or '']
        for code, value in items:
            out.append('%s%s%s' % (code, '' if value is None else value, cls.DELIM))
        frame = ''.join(out)
        if seq is not None:
            frame = '%s%s%d%s' % (frame, cls.SEQ_CODE, int(seq) % 10, cls.CRC_CODE)
            frame = frame + cls.checksum(frame) + '\r'
        return frame


# --------------------------------------------------------------------------- #
# Сервис-диспетчер ACS.
# --------------------------------------------------------------------------- #
def _sip_datetime(now):
    """SIP2 дата/время: ``YYYYMMDD    HHMMSS`` (4 пробела вместо таймзоны)."""
    t = time.localtime(now)
    return time.strftime('%Y%m%d', t) + '    ' + time.strftime('%H%M%S', t)


def _decision_ok(result):
    """Свести результат сида (Decision | bool | None) к ok-флагу + причинам.

    Возвращает ``(ok: bool, reasons: list[str])``.
    """
    if result is None:
        return False, []
    if isinstance(result, bool):
        return result, []
    ok = getattr(result, 'ok', None)
    reasons = list(getattr(result, 'reasons', []) or [])
    if ok is None:
        # Незнакомый объект — трактуем правдивость напрямую.
        return bool(result), reasons
    return bool(ok), reasons


class Sip2Service:
    """ACS-диспетчер SIP2: разбор запроса → операция домена → кадр ответа.

    Все доменные сиды duck-typed и могут быть ``None`` — тогда сервис всё равно
    отдаёт корректный кадр SIP2 с ``ok='0'``/пустыми списками, не падая.
    """

    def __init__(self, circulation=None, readers=None, devices=None, now=None,
                 inst_id='BIBLIO'):
        self.circ = circulation
        self.readers = readers
        self.devices = devices
        self._now = now or time.time
        self.inst_id = inst_id
        self.codec = Sip2Codec
        self._dispatch = {
            MSG_LOGIN: self._login,
            MSG_SC_STATUS: self._sc_status,
            MSG_PATRON_INFO: self._patron_info,
            MSG_ITEM_INFO: self._item_info,
            MSG_CHECKOUT: self._checkout,
            MSG_CHECKIN: self._checkin,
            MSG_RENEW: self._renew,
            MSG_END_SESSION: self._end_session,
        }

    # -- public ------------------------------------------------------------- #
    def handle(self, line):
        """Разобрать запрос, выполнить операцию, вернуть кадр ответа.

        ``AY``-seq запроса эхо-отражается в ответе (с пересчётом CRC). На
        неизвестный id сообщения отдаём 96 (Request SC Resend) — мягкий отказ,
        как в §1 разбора (терминал перешлёт).
        """
        req = self.codec.parse(line)
        seq = req.get('seq')
        handler = self._dispatch.get(req['id'])
        if handler is None:
            # 96 Request SC Resend — неизвестное/неподдержанное сообщение.
            return self.codec.build('96', '', [], seq=seq)
        return handler(req, seq)

    # -- helpers ------------------------------------------------------------ #
    def _resolve_ticket(self, patron_field):
        """AA читателя → билет (abis_code).

        Сначала пробуем ``readers.find_by_card`` (RFID-карта), затем трактуем
        значение как уже-билет. None-сид — возвращаем как есть.
        """
        if not patron_field:
            return patron_field
        if self.readers is not None:
            try:
                rec = self.readers.find_by_card(patron_field)
            except Exception:
                rec = None
            if rec and rec.get('abis_code'):
                return rec['abis_code']
        return patron_field

    @staticmethod
    def _first(fields, code, default=''):
        """Первое значение поля (учёт повторов-списков)."""
        v = fields.get(code, default)
        if isinstance(v, list):
            return v[0] if v else default
        return v

    def _circ_call(self, name, *args):
        """Безопасный вызов метода circulation-сида; None-сид → (False, [])."""
        if self.circ is None:
            return False, []
        fn = getattr(self.circ, name, None)
        if fn is None:
            return False, []
        try:
            return _decision_ok(fn(*args))
        except Exception:
            return False, []

    # -- 93 -> 94 Login ----------------------------------------------------- #
    def _login(self, req, seq):
        # Принимаем любые валидные CN/CO/CP; политику паролей завязываем позже.
        ok = '1'
        return self.codec.build(MSG_LOGIN_RESP, ok, [], seq=seq)

    # -- 99 -> 98 SC/ACS Status --------------------------------------------- #
    def _sc_status(self, req, seq):
        # Фиксированные поля 98: online '1', checkin/checkout 'Y', статус-апдейт
        # 'Y', оффлайн 'N', timeout '000', retries '000', дата, версия '2.00'.
        fixed = '1YYYNNN000000%s2.00' % _sip_datetime(self._now())
        # BX — 16-символьная маска поддерживаемых сообщений (порядок SIP2 v2):
        # patron status / checkout / checkin / block patron / sc/acs status /
        # request resend / login / patron information / end patron session /
        # fee paid / item information / item status update / patron enable /
        # hold / renew / renew all.
        bx = 'YYYNYYYYYNYNNNYN'
        fields = [
            ('AO', self.inst_id),
            ('BX', bx),
            ('AM', 'Biblio'),     # имя библиотеки
            ('AF', 'Biblio SIP2 ACS online'),
        ]
        return self.codec.build(MSG_ACS_STATUS, fixed, fields, seq=seq)

    # -- 63 -> 64 Patron Information ---------------------------------------- #
    def _patron_info(self, req, seq):
        f = req['fields']
        patron = self._first(f, 'AA')
        ticket = self._resolve_ticket(patron)
        # Список книг на руках (AU = charged items).
        charged = []
        if self.circ is not None and getattr(self.circ, 'loans', None):
            try:
                charged = list(self.circ.loans(ticket) or [])
            except Exception:
                charged = []
        # Фиксированные поля 64: patron status (14 'пробелов'=нет блокировок),
        # язык '000', дата.
        status = ' ' * 14
        charged_n = '%04d' % len(charged)
        fixed = '%s000%s' % (status, _sip_datetime(self._now()))
        fields = [
            ('AO', self.inst_id),
            ('AA', ticket or patron or ''),
            ('AE', ''),                  # ФИО (резолв ФИО — отдельный сид)
            ('BL', 'Y' if ticket else 'N'),  # valid patron
            ('CQ', 'Y'),                 # valid patron password (заглушка)
            # Счётчики (charged items count и т.п.) в позициях summary-ответа:
            ('CB', charged_n),           # charged items count
        ]
        for code in charged:
            fields.append(('AU', code))
        return self.codec.build(MSG_PATRON_RESP, fixed, fields, seq=seq)

    # -- 17 -> 18 Item Information ------------------------------------------ #
    def _item_info(self, req, seq):
        f = req['fields']
        item = self._first(f, 'AB')
        status = ITEM_STATUS_UNKNOWN
        if self.circ is not None and getattr(self.circ, 'doc_state', None):
            try:
                st = self.circ.doc_state(item)
            except Exception:
                st = None
            if st:
                status = str(st)
        # 18: CirculationStatus(2) + security marker(2) + fee type(2) + дата.
        fixed = '%s0001%s' % (status[:2].rjust(2, '0'), _sip_datetime(self._now()))
        fields = [
            ('AB', item or ''),
            ('AO', self.inst_id),
            ('AJ', ''),                  # название (резолв — отдельный сид)
        ]
        return self.codec.build(MSG_ITEM_RESP, fixed, fields, seq=seq)

    # -- 11 -> 12 Checkout -------------------------------------------------- #
    def _checkout(self, req, seq):
        f = req['fields']
        patron = self._first(f, 'AA')
        item = self._first(f, 'AB')
        ticket = self._resolve_ticket(patron)
        ok, reasons = self._circ_call('checkout', ticket, item)
        # 12: ok(1) + renewal_ok(1) + magnetic_media('U'nknown) + desensitize +
        # дата.
        fixed = '%s%sUY%s' % ('1' if ok else '0', 'Y' if ok else 'N',
                              _sip_datetime(self._now()))
        fields = [
            ('AO', self.inst_id),
            ('AA', ticket or patron or ''),
            ('AB', item or ''),
            ('CK', '1' if ok else '0'),  # ok-флаг для удобства терминала
        ]
        if not ok:
            fields.append(('AF', self._screen_msg(reasons, 'checkout denied')))
        return self.codec.build(MSG_CHECKOUT_RESP, fixed, fields, seq=seq)

    # -- 09 -> 10 Checkin --------------------------------------------------- #
    def _checkin(self, req, seq):
        f = req['fields']
        item = self._first(f, 'AB')
        patron = self._first(f, 'AA')
        ticket = self._resolve_ticket(patron)
        ok, reasons = self._circ_call('checkin', ticket, item)
        # 10: ok(1) + resensitize(Y) + magnetic_media(U) + alert(N) + дата.
        fixed = '%sYUN%s' % ('1' if ok else '0', _sip_datetime(self._now()))
        fields = [
            ('AO', self.inst_id),
            ('AB', item or ''),
            ('CK', '1' if ok else '0'),
        ]
        if not ok:
            fields.append(('AF', self._screen_msg(reasons, 'checkin denied')))
        return self.codec.build(MSG_CHECKIN_RESP, fixed, fields, seq=seq)

    # -- 29 -> 30 Renew ----------------------------------------------------- #
    def _renew(self, req, seq):
        f = req['fields']
        patron = self._first(f, 'AA')
        item = self._first(f, 'AB')
        ticket = self._resolve_ticket(patron)
        ok, reasons = self._circ_call('renew', ticket, item)
        # 30: ok(1) + renewal_ok(1) + magnetic_media(U) + desensitize + дата.
        # §2.7 разбора: признак успеха терминала = resp[2:4]=='1Y'.
        fixed = '%s%sUY%s' % ('1' if ok else '0', 'Y' if ok else 'N',
                              _sip_datetime(self._now()))
        fields = [
            ('AO', self.inst_id),
            ('AA', ticket or patron or ''),
            ('AB', item or ''),
            ('CK', '1' if ok else '0'),
        ]
        if not ok:
            fields.append(('AF', self._screen_msg(reasons, 'renew denied')))
        return self.codec.build(MSG_RENEW_RESP, fixed, fields, seq=seq)

    # -- 35 -> 36 End Patron Session ---------------------------------------- #
    def _end_session(self, req, seq):
        f = req['fields']
        patron = self._first(f, 'AA')
        ticket = self._resolve_ticket(patron)
        # 36: end session ok 'Y' + дата.
        fixed = 'Y%s' % _sip_datetime(self._now())
        fields = [
            ('AO', self.inst_id),
            ('AA', ticket or patron or ''),
        ]
        return self.codec.build(MSG_END_SESSION_RESP, fixed, fields, seq=seq)

    # -- screen message ----------------------------------------------------- #
    @staticmethod
    def _screen_msg(reasons, default):
        """AF-сообщение на экран терминала из Decision.reasons."""
        if reasons:
            return ', '.join(str(r) for r in reasons)
        return default
