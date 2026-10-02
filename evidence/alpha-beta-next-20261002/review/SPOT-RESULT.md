# Spot 完整现货候选结果

BTCUSDT现货，做多或持有现金，无借币、空头或杠杆。CNY10000、不追加资金，2020-01-01至2026-09-20 UTC（末日不含）；795次有限历史模型会话，登记空窗场景789次。费用、BTC/USDT双币佣金、原日程和先前日期汇率均保留。这是完成的现货证据，全局采用决定单独形成。

| 候选 | 基础成本后CNY CAGR | 连续OHLC代理MDD | 配对门槛结果 |
|---|---:|---:|---|
| 原共识基线 | 51.8503% | 41.2073% | 原基线 |
| 止损后趋势再入场 | 50.5494% | 41.2079% | 年化下降约1.30个百分点，回撤未改善 |
| 持仓参与度补足 | 54.3508% | 41.7765% | 回撤增加约0.57个百分点 |
| ATR收盘退出 | 50.1276% | 41.6724% | 年化下降约1.72个百分点，回撤增加 |
| ATR自适应止损 | 55.2180% | 36.4122% | 四种压力场景均满足登记配对门槛 |
| 20%常驻核心仓 | 50.9822% | 39.7612% | 空窗场景年化较同场景基线下降约1.47个百分点，超过1个百分点容忍度 |
| 20%SMA200核心仓 | 48.6884% | 41.6688% | 年化下降约3.16个百分点，回撤增加 |

ATR自适应止损基础年化提高3.3678个百分点，连续代理回撤降低4.7951个百分点。手续费+50%为54.2139%/36.5591%，成交及止损滑点×2为54.1021%/36.5694%，空窗场景与基础账户相同。它是唯一通过配对门槛的新现货候选；只包含它的组合复用原账户。原100%年化/不超过30%连续回撤目标保持，仍是NOT_MET。

基础账户还有明确的风险权衡：原共识基线最差CNY单日收益为−14.4837424%，ATR自适应止损为−15.8028863%，后者单日损失更大；两者最长水下期均为713天。因此不能声称每个风险维度都改善。

## 实际风险校准与beta

只用2020–2021的731个实际USDT日收益训练。固定比例只影响2022年后新买单，已有持仓不回缩，不缩放或拼接权益曲线。七个完整基础账户重新执行，比例1基线仍逐组等于原账户。atr-stop比例0.9972720085277638，实际校准账户55.1967% CAGR/36.3671%代理MDD。

| 2022年以后实际日收益 | BTC beta | USDT年化波动率 |
|---|---:|---:|
| 原共识基线 | 0.354584 | 29.9915% |
| 校准后ATR止损 | 0.337065 | 29.0160% |

常驻核心仓实际beta0.393244超过基线+0.02的0.374584上限，不能标为风险匹配。其他候选通过风险带也不能跳过四场景采用门槛。独立比例核对重建265808个归属快照和540个成交BUY关联；训练末持币保留，只有新买单缩小。校准后atr-stop验证段累计USDT收益较基线高约27.72个百分点，这是累计收益差，非年化差。验证段HAC7截距95%区间包含0；历史已被研究，不能证明未来alpha。

## 正式共享代码等值证明

Proposal0c52c812301de3712f3637a1ce1b1241de0c40f1 / Python619570fb7baa586f28ad5de2a440d7752a536cc8f8ce7e357264612e65801537通过209项离线检查及独立源码边界审查。Model/session/Lifecycle用完成日线ATR14，止损距离clip(4×ATR14/close,10%,30%)，保留成交后高点、证实的保护下限和穿价普通退出。默认比例1，校准仅诊断。Model v5在恢复前拒绝旧规则或畸形状态，不删除旧目录或猜测迁移。

正式共享路径另跑基础、手续费、滑点、空窗、文件校准基础五个完整账户，每个147笔成交。financial/fills/daily/ownership/operating/remaining_original_fields六组精确等于对应研究账户；另行重算现金/BTC/双币费用/日权益/统计量一致。正式路径不安装AlphaPolicy钩子。旧来源相等门正确拒绝新代码，两个不同来源由独立等值桥另行绑定，不放宽通用验证器。

## 原件与解释边界

原件为/workspace/scratch/alpha-beta-next/spot-singletons/accounts-manifest.json、/workspace/scratch/alpha-beta-next/risk-spot-project-early.json.gz、/workspace/scratch/alpha-beta-next/spot-project-calibration.json、/workspace/scratch/alpha-beta-next/spot-canonical/canonical-inventory.json。完整来源及实际命令/压缩回执保留；后续main不能冒充已测量HEAD。独立依据为spot-actual-risk-financial-review.md、spot-actual-risk-financial-proof.json、spot-actual-risk-sizing-proof.json、spot-canonical-five-financial-review.md。五账户证明SHA c1803ecb6c66a1f6397415ce2b033f569ebca46e6df42419bee87ea45f351b8d。

可移植归档中的相同原件位于evidence根目录下的对应子路径；原始文件字节及raw SHA保持不变，本文路径更正不改写或重标原始财务回执。

连续OHLC代理路径未被第二引擎重放，backup内容未再次打开；原始归档声明通过严格校验及对应来源等值核对。原生交易案例0、实际账户观察日0，NOT_QUALIFIED。未使用私有账户、凭据、订单、转账或账户设置。

以下独立原账户核对报告的SHA绑定本表：

- financial-audit-spot-consensus-v2-final.json: f9066e622622fd281d2ba4506499cf70170f458b19a98a981a648999e1c1aead
- financial-audit-spot-trend-reentry.json: 1a6ab9d562a29f6e1326495aa258ddf408cdc07294b85dce4dd6de04a53a8091
- financial-audit-spot-target-participation.json: ec0761348d9ece7fcdb5fc2e3dd0c88d44a5b8c64434ccb6e30f4a758c6af0be
- financial-audit-spot-atr-close.json: 91902699ca113eee21a71aecde04ad57846b11a8827e2ad044ec7e71a139b73a
- financial-audit-spot-atr-stop.json: a234543735c355d327ab41fb0e87f17386dca477a02dca334c39db324d160330
- financial-audit-spot-core-permanent.json: eb5383722699c89f98749f73b9ec28460900508a958ef9914a13364a6d2d79c7
- financial-audit-spot-core-slow.json: 69fd3563edf1a421d1ece1377beaba0e0bef36e950bd3530af7699cb374b1b4d
