#!/usr/bin/env python3
"""MockStation — эмулятор станции/киоска самообслуживания IDlogic (#272).

Чистый Python-симулятор, который **сценарно** проигрывает полную сессию
самообслуживания читателя против device-facing API Biblio: пинг → опознать
читателя по карте → прочитать метки RFID → книговыдача (роль A, Checkout) →
журнал выдач. Нужен для интеграционных тестов и демо БЕЗ железа и БЕЗ сервера.

НЕ открывает сокетов и НЕ импортирует сервер. Драйвит ИНЪЕКТИРУЕМЫЙ seam
``call`` — ровно форму ``CompatDevicesService.handle(endpoint, payload)``
(см. ``access/compat_devices.py``):

    call(endpoint: str, payload: dict) -> dict | list | bool

В тестах сюда передают фейк с канон-ответами по имени эндпоинта; в реальной
интеграции — лямбду поверх ``Api.route``/``compat.handle``. Имена эндпоинтов —
те же, что принимает шим: ``IsServerAlive``, ``ReaderInfoGet``, ``TagDecode``,
``Checkout``, ``Checkin``, ``GetClientChargedDocs``, ``GateEventAdd`` и т.д.
(DEVICE_CONTROL_MAP.md §книговыдача на станции; contracts/mock_station_spec.md).

Каждый вызов seam пишется в ``transcript`` как кортеж ``(endpoint, payload,
result)`` — для ассертов в тестах и сверки с будущим реальным трейсом.

Сценарные методы устойчивы к falsy/пустым ответам (станция не падает, если
шаг вернул ``[]``/``None``/``False``) — это «гипотеза [I]» из спецификации,
которую мок кодифицирует для проверки.
"""


class MockStationError(Exception):
    """Некорректное использование симулятора (напр. запуск без ``call``)."""


class MockStation:
    """Сценарный эмулятор станции самообслуживания поверх device-facing seam."""

    def __init__(self, call, device_id='station-1'):
        if call is None:
            raise MockStationError('MockStation requires a call seam (got None)')
        if not callable(call):
            raise MockStationError('call seam must be callable')
        self.call = call
        self.device_id = device_id
        self.transcript = []  # список (endpoint, payload, result)

    # -- seam --------------------------------------------------------------- #
    def _invoke(self, endpoint, payload):
        """Дёрнуть seam и записать (endpoint, payload, result) в transcript."""
        result = self.call(endpoint, payload)
        self.transcript.append((endpoint, payload, result))
        return result

    # -- сценарные шаги ----------------------------------------------------- #
    def ping(self):
        """``IsServerAlive`` → bool: жив ли сервер."""
        return bool(self._invoke('IsServerAlive', {'deviceID': self.device_id}))

    def identify_by_card(self, rfid):
        """``ReaderInfoGet`` по RFID-карте → билет (AbisCode) или ``None``."""
        res = self._invoke('ReaderInfoGet', {'rfidCode': rfid})
        if not res:
            return None
        first = res[0] if isinstance(res, list) else res
        if not isinstance(first, dict):
            return None
        return first.get('AbisCode')

    def read_tag(self, hex_block):
        """``TagDecode`` hex-блока метки → itemId (str) или ``None``."""
        res = self._invoke('TagDecode', {'block': hex_block})
        if not isinstance(res, dict):
            return None
        return res.get('ItemId')

    def self_checkout(self, ticket, item_codes):
        """Книговыдача: ``Checkout`` на каждый код. → ``{'issued','denied'}``.

        ``issued`` — коды с ``Success: True``; ``denied`` — список
        ``{'item','reasons'}`` для отказов (или нерешённых ответов).
        """
        issued, denied = [], []
        for code in (item_codes or []):
            res = self._invoke('Checkout', {'abisCode': ticket, 'bookCode': code})
            if isinstance(res, dict) and res.get('Success'):
                issued.append(code)
            else:
                reasons = list(res.get('Reasons') or []) if isinstance(res, dict) else []
                denied.append({'item': code, 'reasons': reasons})
        return {'issued': issued, 'denied': denied}

    def self_checkin(self, ticket, item_codes):
        """Возврат: ``Checkin`` на каждый код. → ``{'returned','denied'}``."""
        returned, denied = [], []
        for code in (item_codes or []):
            res = self._invoke('Checkin', {'abisCode': ticket, 'bookCode': code})
            if isinstance(res, dict) and res.get('Success'):
                returned.append(code)
            else:
                reasons = list(res.get('Reasons') or []) if isinstance(res, dict) else []
                denied.append({'item': code, 'reasons': reasons})
        return {'returned': returned, 'denied': denied}

    def loans(self, ticket):
        """``GetClientChargedDocs`` → список выданных документов читателя."""
        res = self._invoke('GetClientChargedDocs', {'abisCode': ticket})
        return res if isinstance(res, list) else []

    def gate_pass(self, item_code, is_book=1):
        """``GateEventAdd`` — антикражное событие на воротах. → bool."""
        return bool(self._invoke('GateEventAdd', {
            'deviceID': self.device_id, 'bookCode': item_code, 'isBook': is_book}))

    # -- оркестрация -------------------------------------------------------- #
    def run_self_service(self, rfid, hex_blocks):
        """Полная сессия: ping → identify → read tags → checkout → loans.

        Устойчив к falsy-шагам: если сервер мёртв / читатель не опознан / метки
        битые — возвращает связный summary, не падает.

        → ``{'alive', 'ticket', 'items', 'issued', 'denied', 'loan_count'}``.
        """
        alive = self.ping()
        ticket = self.identify_by_card(rfid)
        items = []
        for blk in (hex_blocks or []):
            item = self.read_tag(blk)
            if item:
                items.append(item)
        summary = {'alive': alive, 'ticket': ticket, 'items': items,
                   'issued': [], 'denied': [], 'loan_count': 0}
        if not ticket:
            return summary
        out = self.self_checkout(ticket, items)
        summary['issued'] = out['issued']
        summary['denied'] = out['denied']
        summary['loan_count'] = len(self.loans(ticket))
        return summary
