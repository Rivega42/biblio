#!/usr/bin/env python3
"""Device-facing compat-адаптер — протокольный шим IDlogic → нативные сервисы Biblio.

Узел #272 (COMPAT_ADAPTER_CONTRACT.md, 2/3). Тонкий слой: принимает вызовы,
которые физические устройства/агенты IDlogic (TagService, станции, постаматы)
уже умеют делать (``/easybookdll/*`` + station-facing), и ТРАНСЛИРУЕТ их в
нативные домены Biblio (``devices`` / own-store-RDR / holds / circulation).
НЕ система-источник, НЕ копия ``api.svc``, своей БД нет.

Дизайн — чистый транслятор с инъектируемыми сидами (как ``catalog=`` в
``acquisition.py``): ``handle(endpoint, payload) -> response``. Сиды:
  * ``devices``     — :class:`access.devices.DeviceService` (ОБЯЗАТЕЛЕН): heartbeat,
                      лицензия, мастер-ключи, реестр.
  * ``readers``     — опц. own-store/RDR сид: ``find_by_card(code) -> {abis_code,
                      rfid_code} | None`` и ``bind_card(abis_code, rfid_code,
                      serial, kind) -> bool``. Нет сида ⇒ ReaderInfoGet=[]/
                      ReaderModify=False (graceful, как no-catalog в acquisition).
  * ``holds``       — опц. сид holds (#222) для station-facing заказов (заглушки
                      возвращают пусто до врезки SAFEKEEPER_HOLDS_MAPPING 3/3).

HTTP-врезка (в ``core.Api.route``/app_aiohttp) — отдельный тонкий слой поверх
этого транслятора; здесь — переводимая логика + проверка унаследованного Basic.
"""
import base64

# Унаследованный device-facing логин (захардкожен в resx TagService —
# TAGSERVICE_FUNCTION_MAP §6). Пароль НЕ хранится в коде Biblio: задаётся
# конфигурацией (compat-режим), сравнивается с переданным legacy_pass.
LEGACY_LOGIN = 'ServiceLogin'

# Грант, под которым работает compat-сервис-аккаунт.
COMPAT_GRANT = 'devices.service'

# Карта вида РЛ-карты читателя → нативный kind (own-store/RDR): 28/30/24.
CARD_KIND_MAIN = 'main'   # поле 30
CARD_KIND_EXTRA = 'extra' # поле 24
CARD_KIND_EKP = 'ekp'     # поле 28


class CompatError(Exception):
    """Неизвестный/неподдержанный device-facing вызов."""


def parse_basic(auth_header):
    """``Authorization: Basic base64(login:pass)`` → ``(login, pass)`` | ``None``."""
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != 'basic':
        return None
    try:
        raw = base64.b64decode(parts[1]).decode('utf-8', 'replace')
    except Exception:
        return None
    if ':' not in raw:
        return None
    login, _, pwd = raw.partition(':')
    return login, pwd


class CompatDevicesService:
    """Транслятор device-facing вызовов IDlogic в нативные сервисы Biblio."""

    def __init__(self, devices, readers=None, holds=None, circulation=None,
                 locker=None, codec=None, inventory=None, vision=None, sip2=None,
                 legacy_pass=None, legacy_login=LEGACY_LOGIN):
        self.devices = devices
        self.readers = readers
        self.holds = holds
        self.circulation = circulation
        self.locker = locker  # access.locker.LockerService (station-facing заказы/ячейки)
        self.codec = codec    # access.tag_codec (ISO 28560-2 кодек тега)
        self.inventory = inventory  # access.inventory.InventoryService (ТСД-инвентаризация)
        self.vision = vision        # access.vision.VisionService (камеры/FaceID)
        self.sip2 = sip2            # access.sip2.Sip2Service (SIP2-киоски)
        self.legacy_login = legacy_login
        self.legacy_pass = legacy_pass

    # -- auth --------------------------------------------------------------- #
    def authorize(self, auth_header):
        """Whitelist унаследованного Basic для бесшовного подхвата устройств.

        Включается только если ``legacy_pass`` задан конфигурацией (compat-режим).
        В проде — TLS+токен; этот путь только для существующих устройств IDlogic.
        """
        if self.legacy_pass is None:
            return False
        creds = parse_basic(auth_header)
        if not creds:
            return False
        return creds[0] == self.legacy_login and creds[1] == self.legacy_pass

    # -- dispatch ----------------------------------------------------------- #
    _EASYBOOK = {
        'IsServerAlive', 'LibraryInfoGet', 'ReaderInfoGet', 'ReaderModify',
        'DeviceIsLicenseValid', 'DeviceDataAdd', 'BooksCacheAddUpdate',
        # IAbis (роль A) — реальная книговыдача через circulation-сид:
        'Checkout', 'Checkin', 'Renew', 'GetClientChargedDocs', 'GetDocState',
        'GetUserDebts', 'GetDocInfo', 'SetBookState',
        # Кодек тега ISO 28560-2 (декод/энкод блока) через codec-сид:
        'TagDecode', 'TagEncode',
        # SIP2-кадр (сторонние киоски) через sip2-сид:
        'Sip2',
    }
    _STATION = {'MastersRFIDGet', 'SafeKeeperMasterRFIDModify', 'OrdersGet',
                'SafeKeeperInfoGet2', 'OrderBookProcessedSet', 'OrderModify',
                # Фаза 2 — периметр (ворота/счётчик/полки/СКУД) → devices-сид:
                'GateEventAdd', 'VisitorCountAdd', 'SmartShelfSync', 'AcsPassAdd',
                'BooksOnShelfGet',
                # ТСД-инвентаризация → inventory-сид:
                'InventoryOpen', 'InventoryScan', 'InventoryClose', 'InventoryReport',
                # Камеры/FaceID → vision-сид:
                'FaceEnroll', 'FaceIdentify', 'FaceEventAdd'}

    def handle(self, endpoint, payload=None):
        """Маршрутизировать device-facing вызов. ``endpoint`` — с/без префикса,
        напр. ``'easybookdll/DeviceDataAdd'`` или ``'/las/MastersRFIDGet'``."""
        payload = payload or {}
        name = endpoint.strip('/').split('/')[-1]
        if name in self._EASYBOOK:
            return getattr(self, '_eb_' + name)(payload)
        if name in self._STATION:
            return getattr(self, '_st_' + name)(payload)
        raise CompatError('unsupported device endpoint: %r' % (endpoint,))

    # -- /easybookdll/* ----------------------------------------------------- #
    def _eb_IsServerAlive(self, _p):
        return True

    def _eb_LibraryInfoGet(self, p):
        dev = self.devices.get(p.get('deviceID'))
        if dev is None:
            return []
        return [{'LibraryID': dev.get('library'), 'TS': 0, 'TS1': ''}]

    def _eb_ReaderInfoGet(self, p):
        code = p.get('rfidCode')
        if self.readers is None or not code:
            return []
        r = self.readers.find_by_card(code)
        if not r:
            return []
        return [{'AbisCode': r.get('abis_code'), 'RFIDCode': r.get('rfid_code', code)}]

    def _eb_ReaderModify(self, p):
        if self.readers is None:
            return False
        kind = CARD_KIND_EKP if p.get('serialNumber') else CARD_KIND_MAIN
        return bool(self.readers.bind_card(
            abis_code=p.get('abisCode'), rfid_code=p.get('rfidCode'),
            serial=p.get('serialNumber'), kind=kind))

    def _eb_DeviceIsLicenseValid(self, p):
        return bool(self.devices.is_license_valid(p.get('deviceID')))

    def _eb_DeviceDataAdd(self, p):
        try:
            self.devices.heartbeat(
                p.get('deviceID'),
                soft_online=p.get('softOnlineCount', 1),
                ok_count=p.get('deviceOkCount', 0),
                error_count=p.get('deviceErrorCount', 0))
            return True
        except Exception:
            return False

    def _eb_BooksCacheAddUpdate(self, _p):
        # Кэш прочитанных кодов — идемпотентный no-op в этом слайсе (лог на слое
        # маршрутов). Нативный кэш каталога заведём отдельно при необходимости.
        return True

    # -- IAbis (роль A): книговыдача через circulation-сид -------------------- #
    def _resolve_ticket(self, p):
        """Билет читателя: явный abisCode/readerCard ИЛИ резолв RFID-карты через readers."""
        t = p.get('abisCode') or p.get('readerCard')
        if t:
            return t
        card = p.get('readerRFID') or p.get('rfidCode')
        if card and self.readers is not None:
            r = self.readers.find_by_card(card)
            if r:
                return r.get('abis_code')
        return None

    @staticmethod
    def _decision(res):
        """Свести результат circulation (Decision | bool | None) к device-ответу."""
        if res is None:
            return {'Success': False, 'Reasons': ['not_found']}
        ok = getattr(res, 'ok', None)
        if ok is None:
            ok = getattr(res, 'allow', None)
        if ok is None:
            ok = bool(res)
        out = {'Success': bool(ok), 'Reasons': list(getattr(res, 'reasons', None) or [])}
        computed = getattr(res, 'computed', None) or {}
        if 'due' in computed:
            out['Due'] = computed['due']
        return out

    def _book_code(self, p):
        return p.get('bookCode') or p.get('bookRFID') or p.get('docCode')

    def _eb_Checkout(self, p):
        if self.circulation is None:
            return {'Success': False, 'Reasons': ['no_circulation']}
        ticket, code = self._resolve_ticket(p), self._book_code(p)
        if not ticket or not code:
            return {'Success': False, 'Reasons': ['bad_request']}
        return self._decision(self.circulation.checkout(ticket, code))

    def _eb_Checkin(self, p):
        if self.circulation is None:
            return {'Success': False, 'Reasons': ['no_circulation']}
        ticket, code = self._resolve_ticket(p), self._book_code(p)
        if not ticket or not code:
            return {'Success': False, 'Reasons': ['bad_request']}
        return self._decision(self.circulation.checkin(ticket, code))

    def _eb_Renew(self, p):
        if self.circulation is None:
            return {'Success': False, 'Reasons': ['no_circulation']}
        ticket, code = self._resolve_ticket(p), self._book_code(p)
        if not ticket or not code:
            return {'Success': False, 'Reasons': ['bad_request']}
        return self._decision(self.circulation.renew(ticket, code))

    def _eb_GetClientChargedDocs(self, p):
        if self.circulation is None:
            return []
        ticket = self._resolve_ticket(p)
        return self.circulation.loans(ticket) if ticket else []

    def _eb_GetDocState(self, p):
        if self.circulation is None:
            return []
        code = self._book_code(p)
        st = self.circulation.doc_state(code) if code else None
        return [{'BookCode': code, 'State': st}] if st is not None else []

    def _eb_GetUserDebts(self, p):
        if self.circulation is None:
            return {}
        ticket = self._resolve_ticket(p)
        if not ticket:
            return {}
        d = self.circulation.debts(ticket) or {}
        return {'OnHand': d.get('on_hand'), 'Outstanding': d.get('outstanding'),
                'Level': d.get('debt_level')}

    def _eb_GetDocInfo(self, p):
        if self.circulation is None:
            return []
        code = self._book_code(p)
        info = self.circulation.doc_info(code) if code else None
        return [{'BookCode': code, 'Mfn': info.get('mfn'),
                 'Title': info.get('title')}] if info else []

    def _eb_SetBookState(self, p):
        if self.circulation is None:
            return False
        code = self._book_code(p)
        state = p.get('state') if p.get('state') is not None else p.get('bookState')
        return bool(code and self.circulation.set_doc_state(code, state))

    def _eb_Sip2(self, p):
        """Обработать один SIP2-кадр (строку) и вернуть ответный кадр."""
        if self.sip2 is None:
            return {'Response': None, 'Reasons': ['no_sip2']}
        line = p.get('line') or p.get('frame') or ''
        try:
            return {'Response': self.sip2.handle(line)}
        except Exception:
            return {'Response': None, 'Reasons': ['sip2_error']}

    # -- кодек тега ISO 28560-2 (codec-сид) ---------------------------------- #
    def _primary_oid(self):
        return getattr(self.codec, 'OID_PRIMARY_ITEM_ID', 1)

    def _eb_TagDecode(self, p):
        """Декодировать hex-блок тега → {ItemId, Data}. Битый блок → ItemId None."""
        if self.codec is None:
            return {'ItemId': None, 'Reasons': ['no_codec']}
        hexs = (p.get('block') or p.get('hex') or '').strip()
        try:
            data = self.codec.decode_block(bytes.fromhex(hexs))
        except Exception:
            return {'ItemId': None, 'Reasons': ['bad_block']}
        oid = self._primary_oid()
        item = data.get(oid)
        if item is None:
            item = data.get(str(oid))
        return {'ItemId': (str(item) if item is not None else None),
                'Data': {str(k): v for k, v in data.items()}}

    def _eb_TagEncode(self, p):
        """Закодировать ItemId (OID 1) в hex-блок тега → {Block, ItemId}."""
        if self.codec is None:
            return {'Block': None, 'Reasons': ['no_codec']}
        item = p.get('itemId') or self._book_code(p)
        if not item:
            return {'Block': None, 'Reasons': ['bad_request']}
        try:
            blk = self.codec.encode_block({self._primary_oid(): str(item)})
        except Exception:
            return {'Block': None, 'Reasons': ['encode_error']}
        return {'Block': blk.hex(), 'ItemId': str(item)}

    # -- station-facing (мастер-ключи; заказы/ячейки — слайс 3/3) ----------- #
    def _st_MastersRFIDGet(self, p):
        dev = self.devices.get(p.get('safeKeeperID') or p.get('deviceID'))
        device_id = dev['id'] if dev else None
        masters = self.devices.masters(device_id=device_id)
        return [{'RFID': m['rfid'], 'FIO': m.get('fio'), 'Id': m['id']}
                for m in masters]

    def _st_SafeKeeperMasterRFIDModify(self, p):
        dev = self.devices.get(p.get('safekeeperID') or p.get('deviceID'))
        if dev is None:
            return False
        self.devices.master_modify(p.get('rfidCode') or p.get('rfid'),
                                   fio=p.get('fio'), device_id=dev['id'])
        return True

    # -- station-facing заказы/ячейки → LockerService (slice 3/3) [I] -------- #
    def _sk_device_id(self, p):
        dev = self.devices.get(p.get('safeKeeperID') or p.get('safekeeperID')
                               or p.get('deviceID'))
        return dev['id'] if dev else None

    @staticmethod
    def _order_dto(o):
        cell = o.get('cell_no')
        return {'Id': o['id'], 'StateId': o['state'],
                'ReaderRFID': o['reader_ticket'], 'ReaderFIO': o.get('reader_fio'),
                'CellNumber': cell, 'SafeKeeperId': o['safekeeper'],
                'CellNumberShifted': (cell - o.get('cell_shift', 0)) if cell is not None else None}

    def _st_OrdersGet(self, p):
        if self.locker is None:
            return []
        sk = self._sk_device_id(p)
        orders = self.locker.list_for_safekeeper(sk) if sk is not None else []
        return [self._order_dto(o) for o in orders]

    def _st_SafeKeeperInfoGet2(self, p):
        """Карта ячеек: CellsState (битмаска) + занятые ячейки (наружу для legacy)."""
        if self.locker is None:
            return []
        sk = self._sk_device_id(p)
        if sk is None:
            return []
        busy = sorted(self.locker.busy_cells(sk))
        return [{'CellsState': self.locker.cells_state(sk), 'BusyCells': busy,
                 'BusyCellsCount': len(busy)}]

    def _st_OrderBookProcessedSet(self, p):
        if self.locker is None:
            return False
        self.locker.store.set_item_processed(p.get('orderID'), p.get('bookCode'))
        return True

    def _st_OrderModify(self, p):
        """opID/stateID → операции LockerService. Возврат — Id заказа (как IDlogic)."""
        if self.locker is None:
            return 0
        op, state, oid = p.get('opID'), p.get('stateID'), p.get('id')
        try:
            if op == 1:                       # создать
                sk = self._sk_device_id(p)
                o = self.locker.create(p.get('readerRFID'), sk,
                                       reader_fio=p.get('readerFIO'))
                return o['id']
            if op == 0:                       # отмена/удаление
                self.locker.cancel(oid)
                return oid or 0
            if state == 3:                    # укомплектован
                self.locker.staff(oid, p.get('cellNumber'))
            elif state == 4:                  # выдан
                self.locker.issue(oid)
            return oid or 0
        except Exception:
            return 0

    # -- Фаза 2: периметр (ворота/счётчик/полки/СКУД) → devices-сид ---------- #
    def _st_GateEventAdd(self, p):
        did = self._sk_device_id(p)
        if did is None:
            return False
        self.devices.gate_alarm(did, uid=p.get('uid'), book_code=p.get('bookCode'),
                                book_name=p.get('bookName'), is_book=p.get('isBook', 1))
        return True

    def _st_VisitorCountAdd(self, p):
        did = self._sk_device_id(p)
        if did is None:
            return False
        self.devices.visitor(did, value_in=p.get('valueIn', 0),
                             value_out=p.get('valueOut', 0))
        return True

    def _st_SmartShelfSync(self, p):
        did = self._sk_device_id(p)
        if did is None:
            return False
        items = [{'book_code': it.get('BookCode') or it.get('book_code'),
                  'book_name': it.get('BookName') or it.get('book_name'),
                  'count_takes': it.get('CountTakes') or it.get('count_takes', 0)}
                 for it in (p.get('items') or [])]
        self.devices.shelf_sync(did, items)
        return True

    def _st_BooksOnShelfGet(self, p):
        did = self._sk_device_id(p)
        if did is None:
            return []
        return [{'BookCode': r['book_code'], 'BookName': r.get('book_name'),
                 'CountTakes': r.get('count_takes')}
                for r in self.devices.store.list_shelf(did)]

    def _st_AcsPassAdd(self, p):
        did = self._sk_device_id(p)
        if did is None:
            return False
        kw = {}
        if p.get('direction') is not None:
            kw['direction'] = p['direction']
        self.devices.acs_pass(did, p.get('rfidCode'), client_name=p.get('clientName'),
                              zone=p.get('zone'), **kw)
        return True

    # -- ТСД-инвентаризация → InventoryService ------------------------------ #
    def _st_InventoryOpen(self, p):
        if self.inventory is None:
            return None
        s = self.inventory.open(p.get('db'), p.get('location'), operator=p.get('operator'))
        return {'SessionId': s['id'], 'Status': s['status']}

    def _st_InventoryScan(self, p):
        if self.inventory is None:
            return False
        try:
            self.inventory.scan(p.get('sessionId'), p.get('itemCode'), rfid=p.get('rfid'))
            return True
        except Exception:
            return False

    def _st_InventoryClose(self, p):
        if self.inventory is None:
            return False
        try:
            self.inventory.close(p.get('sessionId'))
            return True
        except Exception:
            return False

    def _st_InventoryReport(self, p):
        if self.inventory is None:
            return {}
        try:
            return self.inventory.report(p.get('sessionId'))
        except Exception:
            return {}

    # -- Камеры / FaceID → VisionService ------------------------------------ #
    def _st_FaceEnroll(self, p):
        if self.vision is None:
            return False
        try:
            self.vision.enroll(p.get('ticket'), p.get('faceToken'), label=p.get('label'))
            return True
        except Exception:
            return False

    def _st_FaceIdentify(self, p):
        if self.vision is None:
            return {'Ticket': None, 'Matched': False}
        r = self.vision.identify(p.get('faceToken'))
        return {'Ticket': r.get('ticket'), 'Matched': r.get('matched', False)}

    def _st_FaceEventAdd(self, p):
        if self.vision is None:
            return False
        self.vision.record_event(self._sk_device_id(p), p.get('faceToken'),
                                 score=p.get('score'), ticket=p.get('ticket'))
        return True
