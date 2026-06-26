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
                 locker=None, legacy_pass=None, legacy_login=LEGACY_LOGIN):
        self.devices = devices
        self.readers = readers
        self.holds = holds
        self.circulation = circulation
        self.locker = locker  # access.locker.LockerService (station-facing заказы/ячейки)
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
    }
    _STATION = {'MastersRFIDGet', 'SafeKeeperMasterRFIDModify', 'OrdersGet',
                'SafeKeeperInfoGet2', 'OrderBookProcessedSet', 'OrderModify'}

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
