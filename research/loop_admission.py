"""Finite read-only plans for mature information and three joint risk routes.

Caller receipts are not authenticated venue state. Plans never submit orders,
enable native execution, or qualify a strategy from an input PASS flag.
"""
import argparse
import json
from pathlib import Path
import time

from research import nine_routes as r, loop_risk as risk, loop_data as data


def execution_plan(packet,now):
    start,end=packet['session_start_ms'],packet['deadline_ms']
    if not start<=now<end or end-start!=300000:raise ValueError('original finite manual session required')
    account=packet['account'];book=packet.get('book');queue=packet.get('queue_evidence')
    if (account['symbol']!='BTCUSDT' or account['owned'] is not True or account['protected'] is not True
            or account['pending'] is not False or not 0<=now-account['receipt_ms']<=60000):
        return dict(status='BLOCK_UNKNOWN_ACCOUNT',orders=0)
    if (not book or not queue or type(book.get('available_ms')) is not int
            or not 0<=now-book['available_ms']<=5000 or queue.get('candle_touch_only') is not False
            or type(queue.get('available_ms')) is not int or not 0<=now-queue['available_ms']<=5000
            or len(queue.get('trade_tape_sha256',''))!=64 or len(queue.get('queue_receipt_sha256',''))!=64):
        return dict(status='WAIT_EXECUTION_EVIDENCE',orders=0,account_entrant=False)
    bid,ask=r.number(book['bid']),r.number(book['ask'])
    if not 0<bid<=ask:raise ValueError('invalid contemporaneous book')
    quantity=r.number(packet['remaining_owned_request_btc'],nonnegative=True)
    if quantity<=0:return dict(status='NO_REMAINING_REQUEST',orders=0)
    if end-now<=20000+5000:return dict(status='NO_LIMIT_WAIT_BUDGET',orders=0)
    return dict(status='RESEARCH_20SECOND_LIMIT_THEN_RECONCILE',limit_price=str(bid),quantity_btc=str(quantity),
        cancel_and_query_by_ms=now+20000,deadline_ms=end,fallback='Only confirmed remainder within original capacity/protection and deadline.',
        unknown_response='Persist identity and query; never blindly resend.',orders=0,account_entrant=False,
        maker_fill_proven=False,meaning='Recorded evidence references admit a plan only. Actual queue matching/fills and independent account comparison are still required.')


def decide(route,packet,now):
    if route=='drawdown':
        state=risk.brake_state(packet.get('state'),packet.get('known_closes',[]),packet['accounts'],now)
        account=next(a for a in packet['accounts'] if a['kind']=='coin')
        return dict(state=state,plan=risk.brake_plan(state,account,packet.get('requested_btc')))
    if route=='implied':
        factor=risk.implied_factor(packet['iv'],packet['prior_rms'],packet['available_ms'],now)
        return dict(status='RESEARCH_NEW_BUDGET_FACTOR',factor=str(factor),orders=0,directional_alpha=False,
            account_entrant=False,meaning='Sizing calculation; economic predictor gate must pass separately.')
    if route=='protection':return risk.protection_plan(packet['accounts'],packet['books'],now)
    if route=='execution':return execution_plan(packet,now)
    raise ValueError('unknown preregistered route')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--route',choices=('drawdown','implied','protection','execution'),required=True);args=p.parse_args(argv)
    raw=args.input.read_bytes();packet=json.loads(raw);now=packet['now_ms']
    if type(now) is not int or now>int(time.time()*1000):raise ValueError('future research receipt clock')
    verdict=decide(args.route,packet,now)
    verdict.update(format='btc-loop-read-only-plan-v1',source=data.source(),input_sha256=r.sha(raw),
        spec_sha256=r.sha(data.SPEC.read_bytes()),route=args.route,native_authenticated=False,native_enabled=False,orders=0)
    data.new_json(args.out,verdict);print(json.dumps(r.serial(verdict)))


if __name__=='__main__':main()
