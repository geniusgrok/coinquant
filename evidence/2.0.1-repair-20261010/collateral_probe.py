"""Pure sizing/holding probe; no exchange requests or account-state writes."""
from decimal import Decimal as D
from pathlib import Path
from types import ModuleType
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
CANDIDATE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE / 'coinquant-fix-risk'
ORIGINAL_HEAD = '162ee7138952925ffafbc9b68be7c754c0c0a6c3'
sys.path.insert(0, str(CANDIDATE))
from coinquant import native_preview as fixed
from coinquant.opportunities import Opportunity
from tests.test_native_preview import NativePreviewTests


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for part in iter(lambda: source.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


old_bytes = subprocess.check_output(['git', 'show', ORIGINAL_HEAD + ':coinquant/native_preview.py'], cwd=CANDIDATE)
original = ModuleType('coinquant.original_native_preview')
original.__package__ = 'coinquant'
exec(compile(old_bytes, ORIGINAL_HEAD + ':coinquant/native_preview.py', 'exec'), original.__dict__)

model, reader, snapshot, _, instrument = NativePreviewTests().fixture()
model.model.active = Opportunity(model.last, 1, D(99), D(200), model.last + 14400000)
fixture = {}
for name, implementation in (('original', original), ('fixed', fixed)):
    plan = implementation.entry_preview(reader, model, snapshot)
    q, entry, fee, margin = (D(plan[k]) for k in ('quantity_btc', 'entry_estimate', 'fee', 'allocated_margin_usdt'))
    wallet = D(snapshot['wallet_usdt']) - q * entry * fee
    fill = dict(campaign=plan['campaign'], stop_budget=plan['stop_budget_usdt'],
                sizing_capital=plan['sizing_capital_usdt'], stop_slippage_fraction=plan['stop_slippage_fraction'])
    protection = dict(campaign=plan['campaign'], stop=plan['stop'])
    observations = []
    for mark in map(D, ('100', '99.995', '99.5', '99.000001')):
        held = dict(snapshot, quantity_btc=str(q), entry=str(entry), wallet_usdt=str(wallet),
                    equity_usdt=str(wallet + q * (mark - entry)), isolated_wallet_usdt=str(margin), mark_price=str(mark))
        risk = implementation.holding_risk(held, protection, fill, instrument, fee,
            paid_commission_usdt=q * entry * fee, realized_pnl_usdt=0, paid_funding_usdt=0,
            loss_fraction=reader.loss_fraction, slip_fraction=reader.slip_fraction)
        observations.append(dict(mark=str(mark), action=risk['action'], reason=risk['reason'],
                                 margin_cap_usdt=risk['margin_cap_usdt']))
    fixture[name] = dict(quantity_btc=str(q), entry=str(entry), stop=plan['stop'],
                         margin_usdt=str(margin), observations=observations)
assert fixture['original']['observations'][1]['reason'] == 'isolated_margin_cap'
assert all(row['action'] == 'hold' for row in fixture['fixed']['observations'])

inputs = json.loads((HERE / 'collateral_inputs.json').read_text())
archive = HERE / 'collateral_observations_excerpt.jsonl'
assert digest(archive) == inputs['excerpt_sha256']
source_reports = {}
with archive.open() as source:
    for line in source:
        row = json.loads(line)
        if row['sequence'] in (86, 98, 99):
            source_reports[str(row['sequence'])] = row['report']
        if row['sequence'] >= 99:
            break
assert source_reports['99']['model_preview']['entry_constraint'] == 'isolated_margin_cap'

first = source_reports['86']['actual']
q, price, stop, fee, mmr = D('.337'), D(first['entry']), D('7072.60'), D('.00075'), D('.005')
margin = D(first['isolated_wallet_usdt'])
capital = D(first['wallet_usdt']) + q * price * fee
# The preserved native margin is rounded up at 8 decimal places. Inversion
# gives an explicitly approximate preflight mark, not a new market observation.
mark = (stop - (q * price - margin) / (q * (1 - mmr - fee))) / D('.1')
rules_path = HERE / 'collateral_probe_rules.json'
assert digest(rules_path) == inputs['rules_sha256']
rules = json.loads(rules_path.read_text())['instrument']
v = dict(price=price, mark=mark, fee=fee, mmr=mmr, cap=D('100000000'), instrument=rules,
         capacity=D('78.232') / 4, wallet=capital, available=capital, capital=capital,
         equity=capital, margin_step=D('.00000001'))
requested = capital * D('.10') / original._loss_per_btc(1, price, stop, fee, D('.01'))
historical_sizing = {}
for name, implementation in (('original', original), ('fixed', fixed)):
    extra = {} if name == 'original' else dict(stop_slippage_fraction=D('.01'))
    plan = implementation._funded_quantity(v, 1, stop, D('10228.00'), requested, **extra)
    qty = plan['quantity']
    threshold = price + (plan['margin'] / D('.25') - (capital - qty * price * fee)) / qty
    historical_sizing[name] = dict(**plan, margin_breach_mark=threshold,
        margin_breach_from_entry_percent=(threshold / price - 1) * 100)
assert historical_sizing['original']['quantity'] == D('.337')
assert historical_sizing['fixed']['quantity'] == D('.311')

proof = dict(kind='pure-source-and-original-observation-collateral-probe', no_account_requests=True,
    original_head=ORIGINAL_HEAD,
    original_native_preview_sha256=hashlib.sha256(old_bytes).hexdigest(),
    fixed_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE, text=True).strip(),
    fixed_native_preview_sha256=digest(CANDIDATE / 'coinquant/native_preview.py'),
    probe_sha256=digest(Path(__file__)), fixture=fixture,
    first_historical_trade=dict(original_archive_sha256=inputs['private_original_archive_sha256'],
        excerpt_sha256=digest(archive), reports=source_reports,
        inferred_mark_from_rounded_margin=str(mark), inference_limitation='not an exact recovered market observation',
        sizing_from_same_inferred_mark=historical_sizing),
    economic_limitation='This probe proves the sizing/holding inconsistency and the first observed exit cause. It is not a full-window economic attribution or a return forecast.')
destination = Path(__file__).with_suffix('.json')
destination.write_text(json.dumps(proof, default=str, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(path=str(destination), sha256=digest(destination), passed=True)))
