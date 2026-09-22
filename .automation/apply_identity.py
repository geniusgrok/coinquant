"""Apply the reviewed Coinquant identity consistently to this fixed source tree."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path.cwd()
OLD = 'pancakequant'
NEW = 'coinquant'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rename(text):
    text = text.replace('ychenracing/' + OLD, 'geniusgrok/' + NEW)
    text = re.sub(OLD, lambda m: NEW.upper() if m[0].isupper() else NEW.capitalize() if m[0][0].isupper() else NEW, text, flags=re.I)
    return text.replace('pq-', 'cq-')

# Preserve the complete market-independent draw sequence, not a project-name seed.
spec_path = ROOT / 'research/spec.json'
frozen = json.loads(spec_path.read_text())
seed = frozen['seed']
from datetime import datetime
stamp = lambda t: int(datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp() * 1000)
current = stamp(frozen['start'])
end = stamp(frozen['end'])
draws = []
while current < end:
    draw = int.from_bytes(hashlib.sha256(f'{seed}|{len(draws)}'.encode()).digest()[:8], 'big')
    draws.append(draw)
    current += frozen['gap_hours'][draw % len(frozen['gap_hours'])] * 3_600_000
payload = (json.dumps(draws, indent=2) + '\n').encode()
schedule_sha = sha(payload)

# This obsolete publisher packet is not a current runtime or economic dataset.
shutil.rmtree(ROOT / '.transfer')
paths = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
for name in paths:
    if not name or name.startswith(('.transfer/', '.automation/')):
        continue
    path = ROOT / name
    raw = path.read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        assert not re.search(OLD.encode(), raw, re.I), name
        continue
    text = re.sub(r'"seed"\s*:\s*' + re.escape(json.dumps(seed)),
                  '"invocation_draws_sha256": ' + json.dumps(schedule_sha), text)
    text = rename(text)
    text = text.replace('No .transfer restoration.', '')
    text = text.replace('代码、tests、.github、.transfer及根目录文件', '代码、tests、.github及根目录文件')
    if text.encode() != raw:
        path.write_bytes(text.encode())

(ROOT / OLD).rename(ROOT / NEW)
for p in sorted(ROOT.rglob('*'), key=lambda p: len(p.parts), reverse=True):
    if '.git' in p.parts:
        continue
    if re.search(OLD, p.name, re.I):
        target = p.with_name(rename(p.name))
        assert not target.exists(), target
        p.rename(target)
(ROOT / 'research/invocation_draws.json').write_bytes(payload)

path = ROOT / 'coinquant/research.py'
text = path.read_text()
text = text.replace("    current, index, skip_until = start, 0, -1\n", '''    schedule_path = SPEC_PATH.with_name('invocation_draws.json')
    try:
        raw = schedule_path.read_bytes()
        draws = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise Blocked('frozen invocation sequence unavailable') from exc
    if (hashlib.sha256(raw).hexdigest() != value.get('invocation_draws_sha256')
            or not isinstance(draws, list) or not draws
            or any(type(draw) is not int or not 0 <= draw < 2**64 for draw in draws)):
        raise Blocked('frozen invocation sequence identity invalid')
    current, index, skip_until = start, 0, -1
''')
text = text.replace("    while current < end:\n", "    while current < end:\n        if index >= len(draws):\n            raise Blocked('requested window exceeds frozen invocation sequence')\n")
old_line = '        draw = int.from_bytes(hashlib.sha256(f\'{value["seed"]}|{index}\'.encode()).digest()[:8], \'big\')'
assert old_line in text
text = text.replace(old_line, '        draw = draws[index]')
path.write_text(text)

path = ROOT / 'coinquant/cli.py'
text = path.read_text().replace('Bounded Binance BTCUSDT observation; research migration incomplete.',
    'Coinquant Binance BTCUSDT observation; execution requires economic and safety qualification.')
path.write_text(text)
for path in [ROOT / 'coinquant/binance.py', *ROOT.glob('evidence/**/measured_source/binance.py')]:
    text = path.read_text().replace('read_only_migration_observation', 'read_only_observation')
    text = text.replace('legacy intent kinds stay pending rather than being guessed/migrated.',
                        'unsupported intent kinds stay pending; never infer resolution.')
    path.write_text(text)

# Current operating documentation: no repository-move narrative or alias layer.
(ROOT / 'AGENTS.md').write_text('''# Coinquant engineering rules

Repository: geniusgrok/coinquant. Use the personal / geniusgrok GitHub connection.

## Current mandate

Maintain one manually triggered BTC perpetual system, one quantitative model, one Binance exchange adapter, and one current configuration. Binance BTCUSDT USDT-settled linear perpetual is the only target market. Strategy, risk, dependencies and architecture may be replaced when evidence supports the change. Retained Bybit/OKX evidence is historical research, not a production support requirement.

Economic targets remain cost-net CAGR >= 150% and continuous full-account MDD < 50%, from 2020-01-01T00:00:00Z through 2026-09-20T00:00:00Z exclusive. Start with CNY 10,000 and no additions; include contract history, costs, funding, liquidation, CNY/USDT valuation and the frozen sparse invocation sequence. Research-frequency success does not substitute for sparse acceptance. Do not move the window, lower targets, fabricate data, or describe proxy results as production qualification.

The frozen market-independent draws are in research/invocation_draws.json; research/spec.json binds their SHA-256. Keep the complete normal and absence-stress invocation sequences fixed. Names and repository metadata must not determine economic inputs.

## Development baseline

Main is the canonical development/integration baseline, not certification of production safety or profitability. Read the real remote HEAD before writes. Use normal fast-forward or PR merge operations and respect GitHub protection. Do not force push, overwrite parallel work, or delete historical research branches. New work starts from current main; short-lived branches may isolate changes and then normally merge back.

SX60 remains a research candidate. Do not silently replace the 3.6 reference/default paths, enable execute, relax trading safety, or authorize real/Testnet orders or account changes. Qualification remains NOT_QUALIFIED until its actual evidence passes. Keep engineering integration, research candidate selection, and production enablement separate.

## Execution safety

Default read-only. Live execution requires explicit current authorization and a matching configured account. Engineering tasks do not authorize trading, transfers, credentials or account-setting changes. Reconcile positions, ordinary and conditional orders, and fills before deciding. Unknown responses are neither failure nor success: persist intent and query stable identity before retry. An unavailable account query never means an empty account.

Use one-way isolated positions with exchange leverage fixed at 20, not necessarily 20x account exposure. Filled exposure needs native full-position TP/SL including partial fills. Protection must survive process exit. Do not leave entry remainders able to reopen unprotected exposure after a stop. Keep valid protection during amendments. Unknown funds, orders or protection stop new exposure; only explicitly authorized risk reduction is allowed. Do not invent offline client actions or substitute a background daemon for run_once.

The Python package is coinquant, the Binance credential variables are COINQUANT_BINANCE_KEY and COINQUANT_BINANCE_SECRET, and client IDs use cq-. Preserve the configured account state directory and reconcile durable intents before any action; never treat a new empty directory as proof that the account is flat.

## Engineering and verification

Understand real call paths. Reuse shared account, sizing, campaign and execution components. Keep the production path small; avoid obsolete strategy/adapter compatibility and unrelated refactors. Apply available PonyTail when relevant; absence of the skill is not a reason to invent its use or block independent work. No mandatory TDD, coverage target or redundant approval process.

Use risk-driven minimum necessary validation for funds, orders, idempotency, protection, causality and sparse execution. Reuse economic evidence only when source/config/input identities still apply. Historical source digests identify their recorded measurement, not the current working tree. Missing native checks remain unverified. Neither accounting identity nor unit tests prove economic or live-trading qualification.

Keep one lightweight CI workflow, one Python environment and timeout-minutes: 10. No real-account secrets, scheduled trading, optimization or full historical research in CI. Normal CI has contents: read. Remove temporary publishing tools before integration.

## Preservation and recovery

Preserve meaningful code, configuration, reports and complete economic originals. Prefer native Git and file-backed/programmatic transfers, then authorized connectors. Do not route full archives/Base64/huge JSON through model context. Use verified parts when needed, with fixed source versions and length/hash checks; verify remote bytes, Git objects, tree, commit and target ref. Inspect remote state before retrying an unknown write.

Use PROJECT_STATE.md as the current recovery entry and HANDOFF_PROMPT.md for continuation; do not create duplicate progress systems. Historical source snapshots are not current code and must not overwrite main. A merge, PR or checkpoint does not complete the 150%/<50% objective.
''')

path = ROOT / 'README.md'
text = path.read_text()
text = re.sub(r'当前仓库为.*?\n\n', '仓库：`geniusgrok/coinquant`。\n\n', text, count=1)
text = text.replace('2026-09-22 用户明确授权把研究成果合并 main，后续从实时 main 继续开发。此授权取代旧的“经济达标前不得合并 main”，不降低收益目标，也不授权真实交易、Testnet 写入或账户设置变动。历史研究分支及原件保留。',
                    'main 是当前开发与集成基线。经济资格和原生安全资格必须独立取得；工程修改不授权真实交易、Testnet 写入或账户设置变动。')
text = text.replace('本次源码发布与主线迁移没有重新运行经济账户。', '这些结果不是当前源码的新运行结果。')
text = text.replace('不要用旧 `.transfer` 或任何历史源码快照覆盖当前 main。', '不要用历史源码快照覆盖当前 main。')
text = text.replace('`python -m coinquant` 与 `main.py` 共用 Binance 入口。', '`python -m coinquant` 与 `main.py` 共用 Binance 入口。项目仅使用 `coinquant` 包名和 `COINQUANT_*` 环境变量。')
text = text.replace('同一账户只在一台机器运行。', '默认状态目录是 `~/.coinquant/binance-btcusdt`。已有账户必须继续使用其实际持久化目录，不得丢弃未决意图或把新建空目录当作空仓证明。\n\n同一账户只在一台机器运行。')
text = text.replace('固定经济源码哈希与Library原件一致。', '历史经济源码哈希对应记录的测量身份，不代表当前源码字节。')
text += '\n正式稀疏时间表由 `research/invocation_draws.json` 固定，并由 `research/spec.json` 的 SHA-256 约束；完整正常序列及缺席压力序列不随项目名称变化。\n'
path.write_text(text)

path = ROOT / 'PROJECT_STATE.md'
text = path.read_text()
text = re.sub(r'\A.*?(?=## 当前经济证据)', '''# Coinquant 当前状态

仓库：`geniusgrok/coinquant`；连接：personal / geniusgrok；开发基线：实时 main。main 可正常开发和集成，但经济与原生安全资格仍未完成。

## 运行与证据

Python 3.13；运行入口 `python -m coinquant` 或 `main.py`。只读 Binance BTCUSDT 观察与模型预览；`run --execute` 在凭据和网络访问前拒绝。凭据变量为 `COINQUANT_BINANCE_KEY`、`COINQUANT_BINANCE_SECRET`，默认状态目录 `~/.coinquant/binance-btcusdt`。B36 默认/参考不自动替换为 SX60。

正式调用的固定数列在 `research/invocation_draws.json`，由 `research/spec.json` 的 SHA-256 绑定；正常795次、缺席压力787次。经济账户、费用、杠杆、资金与资格门槛保持冻结。CI 只执行离线检查，不访问交易账户。

经济原件按 `evidence/sustainable-capital-exit-20260922/originals.json` 中的 Library ID、文件 ID、长度和哈希读取。历史摘要中的源码哈希属于当时测量版本，不应当作当前工作区的完整性证明；当前源码以实时 Git tree 和 CI 为准。完整原件、失败结果、风险缺口保留，不用摘要替代。

''', text, flags=re.S)
text = text.replace('本次新回测', '当前源码的新回测').replace('源码发布没有改变这些结果的测量身份。', '这些结果保留其原测量身份，不代表当前源码已重新回测。')
text = text.replace('从实时main核验新引擎及以上原件恢复；', '从实时main核验引擎及以上原件；').replace('不回退到只发布报告的旧状态。', '不把研究候选当生产默认。')
path.write_text(text)

path = ROOT / 'HANDOFF_PROMPT.md'
text = path.read_text()
text = re.sub(r'继续 geniusgrok/coinquant.*?(?=保留原目标：)', '''继续 geniusgrok/coinquant，全程中文，使用 personal / geniusgrok GitHub 连接。遵循当前 AGENTS.md；实际可用时采用 PonyTail，不增加不必要流程。main 是开发集成基线，不是实盘资格。

先读取实时 main、AGENTS.md、PROJECT_STATE.md、evidence/sustainable-capital-exit-20260922/{REPORT.md,SELECTION.json,originals.json} 及对应源码。包名和入口为 coinquant，凭据环境变量为 COINQUANT_BINANCE_KEY、COINQUANT_BINANCE_SECRET。仅使用当前接口，不增加别名或回退入口。

冻结调用数列位于 research/invocation_draws.json，由 research/spec.json 的 SHA-256 约束；完整正常795次、缺席压力787次。历史经济摘要中的源码哈希属于记录的测量，不是当前源码的新验证。复用经济证据前仍须核对语义、配置和数据身份；CI 状态查询实际 SHA。

''', text, flags=re.S)
text = text.replace('本次源码迁移没有新经济回放。', '这些是已保存经济结果，不是当前源码的新回放。')
path.write_text(text)

# Strengthen the two directly changed contracts without adding a broad audit suite.
path = ROOT / 'tests/test_state.py'
text = path.read_text().replace('    def test_deterministic_id_scope(self):\n',
    "    def test_deterministic_id_scope(self):\n        self.assertTrue(client_id('live:123', 123, 'increase').startswith('cq-'))\n")
path.write_text(text)

print(json.dumps({'draws': len(draws), 'draws_sha256': schedule_sha}, sort_keys=True))
