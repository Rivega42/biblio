#!/usr/bin/env python3
"""BDP сквозной e2e (мок-агент, без железа) — капстоун волны E2 (#418).

Прогоняет нативный контракт BDP на РЕАЛЬНЫХ доменных сервисах Biblio + мок-агент
шкафа (физика по шагам, без RPi). Доказывает, что G1..G7 склеиваются в
демонстрируемый флоу выдачи/возврата — основа демостенда «шкаф+VPS» без железа.

Проверяет:
  * device-token → контекст {device_id,tenant,kind} (#413);
  * resolve_patron(uid) → билет (#417);
  * выдача: reserve(op_id) → мок-физика → commit → активная loan (#415/#412);
  * sync.replay: повтор reserve(op_id) идемпотентен;
  * возврат: item.detected(EPC) → find_exemplar_by_tag → инв.№ → return_item (#411);
  * зеркало ячеек cabinet_cell occupied→free→awaiting_extraction (#414);
  * сбой физики → rollback (компенсация резерва).

Standalone (дом. стиль)::  py -3.12 tests/test_bdp_e2e.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from access import seed_vocab
from access.catalog import CatalogStore
from access.store import AccessStore
from access.circulation import (
    CirculationStore, CirculationEngine, default_policy, ALLOW, SECONDS_PER_DAY,
)
from access.readers import ReaderStore, ReaderService, KIND_MAIN
from access.devices import DeviceStore, DeviceService, KIND_SELF_SERVICE_CABINET

PASS = [0]
FAIL = [0]
T0 = 1_700_000_000
DB = 'IBIS'


def check(name, cond):
    if cond:
        PASS[0] += 1
        print('  ok  ', name)
    else:
        FAIL[0] += 1
        print('  FAIL', name)


class MockCabinetAgent:
    """Мок «рук» шкафа: исполняет намерение BDP по шагам, без железа."""
    STEPS = ('take_shelf', 'to_window', 'wait_user', 'give_shelf')

    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.progress = []

    def execute(self, op_id):
        for step in self.STEPS:
            self.progress.append((op_id, step))          # op.progress (WS)
            if self.fail_at == step:
                return {'op_id': op_id, 'status': 'failed', 'step': step}
        return {'op_id': op_id, 'status': 'ok'}           # op.result


def _catalog():
    acc = AccessStore(':memory:')
    seed_vocab.seed_vocabularies(acc, from_catalog=False)
    cat = CatalogStore(':memory:', access_store=acc)
    rec = {'920': 'PAZK', '200': [{'a': 'Демо-книга'}], '700': [{'a': 'Автор А.'}],
           '610': [{'': 'демо'}], '101': 'rus', '907': [{'a': 'Оператор'}],
           '910': [{'a': '0', 'b': 'INV-1', 'h': 'EPC-1'}]}
    res = cat.save(DB, rec)
    return cat, res


def e2e():
    print('-- BDP e2e: выдача + возврат мок-агентом (#418)')
    cat, saved = _catalog()
    check('каталог: демо-книга сохранена (910^h=EPC-1)', saved.get('saved') is True)

    circ = CirculationEngine(store=CirculationStore(':memory:'), policy=default_policy())
    circ.store.add_reader('T-9', category='В01')
    readers = ReaderService(ReaderStore(':memory:'))
    readers.bind_card('T-9', 'CARD-9', kind=KIND_MAIN)
    dev = DeviceService(DeviceStore(':memory:'))
    cab = dev.register('cab-1', KIND_SELF_SERVICE_CABINET, name='Демо-шкаф', tenant='libDemo')
    tok = dev.issue_token(cab['id'])
    dev.cell_upsert('libDemo', cab['id'], 'FRONT', 1, 9, state='occupied', item='INV-1', epc='EPC-1')

    # 0) device-token → контекст шкафа
    ctx = dev.authenticate_token('Bearer ' + tok['token'])
    check('device-token → контекст шкафа',
          bool(ctx) and ctx['kind'] == KIND_SELF_SERVICE_CABINET and ctx['tenant'] == 'libDemo')

    # 1) идентификация карты
    who = readers.resolve_patron('main', 'card-9')
    check('resolve_patron(card) → билет T-9', who['status'] == 'ok' and who['patron'] == 'T-9')

    # 2) ВЫДАЧА: reserve → мок-физика → commit
    op = 'demo-issue-1'
    d = circ.reserve(who['patron'], 'INV-1', T0, op_id=op, device_id=cab['id'])
    check('reserve → PENDING-loan', d.decision == ALLOW and d.computed['loan']['pending'] == 1)
    agent = MockCabinetAgent()
    res = agent.execute(op)
    check('мок-агент отработал физику (ok)', res['status'] == 'ok' and len(agent.progress) == 4)
    c = circ.commit(op, device_id=cab['id'])
    check('commit → активная выдача', c.decision == ALLOW and c.computed['loan']['pending'] == 0)
    loan_id = c.computed['loan']['id']
    check('книга на руках', circ.store.count_on_hand('T-9') == 1)
    dev.cell_upsert('libDemo', cab['id'], 'FRONT', 1, 9, state='free', item=None, epc=None)
    check('ячейка освобождена', dev.store.cabinet_cell_get(cab['id'], 'FRONT', 1, 9)['state'] == 'free')

    # 3) sync.replay идемпотентность
    d2 = circ.reserve(who['patron'], 'INV-1', T0, op_id=op)
    check('replay reserve идемпотентен',
          d2.computed.get('replayed') is True and circ.store.count_on_hand('T-9') == 1)

    # 4) ВОЗВРАТ: EPC → инв.№ → return_item
    ex = cat.find_exemplar_by_tag(DB, 'EPC-1')
    check('item.detected: find_exemplar_by_tag(EPC-1) → INV-1',
          ex is not None and ex[2].get('b') == 'INV-1')
    back = circ.return_item(loan_id, T0 + SECONDS_PER_DAY, device_id=cab['id'])
    check('return_item проведён', back.decision == ALLOW)
    check('после возврата на руках 0', circ.store.count_on_hand('T-9') == 0)
    dev.cell_upsert('libDemo', cab['id'], 'BACK', 2, 3, state='awaiting_extraction',
                    item='INV-1', epc='EPC-1')
    check('возвращённая книга → awaiting_extraction',
          any(x['state'] == 'awaiting_extraction' for x in dev.cell_map('libDemo', cab['id'])))

    # 5) сбой физики → rollback (компенсация)
    op2 = 'demo-issue-2'
    circ.reserve('T-9', 'INV-1', T0, op_id=op2)
    check('второй reserve → PENDING', circ.store.count_on_hand('T-9') == 1)
    bad = MockCabinetAgent(fail_at='give_shelf')
    rr = bad.execute(op2)
    check('мок-агент упал на give_shelf', rr['status'] == 'failed')
    rb = circ.rollback(op2, device_id=cab['id'])
    check('rollback компенсировал резерв',
          rb.decision == ALLOW and circ.store.count_on_hand('T-9') == 0)


def main():
    e2e()
    print('\n%d passed, %d failed' % (PASS[0], FAIL[0]))
    return 1 if FAIL[0] else 0


if __name__ == '__main__':
    sys.exit(main())
