"""Hash-bound frozen feature book and actual finite-alpha proposal screening.

Receipts are requalified from raw bytes; a caller's FEATURE_READY flag cannot
turn future or retroactively downloaded values into historical information.
"""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path

from research import nine_routes as r, nine_data as data, persistent_data as prior


class FeatureBook:
    def __init__(self, folders, inherited=(), etf=None):
        self.sources=[];self.persistent=[];self.bindings=[]
        for folder in map(Path,folders):
            raw=(folder/'receipts.json').read_bytes();packet=json.loads(raw);source={}
            for receipt in packet['receipts']:
                if receipt['name'] in ('etf-demand','old-coin-supply','sofr','iorb'):
                    source[receipt['name']]=data.read_source(folder,receipt,receipt['name'])
            self.sources.append(source);self.bindings.append((str(folder),r.sha(raw)))
            if any(row['name']=='btc-oi' or row['name'].startswith('option-') for row in packet['receipts']):self.persistent.append(prior.qualify(folder))
        for folder in map(Path,inherited):
            raw=(folder/'receipts.json').read_bytes();self.persistent.append(prior.qualify(folder));self.bindings.append((str(folder),r.sha(raw)))
        if etf:
            folder=Path(etf);raw=(folder/'receipts.json').read_bytes()
            receipt=next(row for row in json.loads(raw) if row['name']=='btc-etf-flow')
            self.sources.append({'etf-demand':data.read_source(folder,receipt,'etf-demand')})
            self.bindings.append((str(folder),r.sha(raw)))
        self.sha256=r.sha(json.dumps(self.bindings,sort_keys=True).encode())

    def at(self,family,now,context=None):
        return data.features(self.sources,self.persistent,now,context)['families'][family]


def screen(book,opportunities,family,expression,context_provider):
    """Eligibility at real owned decision clocks precedes any wallet creation."""
    events=[];pending={}
    for proposal in opportunities:
        at=proposal['at_ms'];feature=book.at(family,at,context_provider(at))
        effect=r.alpha_expression(family,expression,feature,proposal,owned=proposal.get('owned') is True)
        if effect['status'] in ('CHANGE_NEW_BUDGET','PROPOSE_NEW_PRIMARY_RESEARCH'):
            events.append(dict(id=proposal['id'],at_ms=at,feature=feature,effect=effect))
        elif effect['status']=='WAIT_QUALIFIED_DATA':pending[feature['status']]=pending.get(feature['status'],0)+1
    # Coverage/action screen is not net economic information validation.
    independent={e['id'] for e in events}
    return dict(status='INFORMATION_EFFECT_PENDING' if independent else 'WAIT_QUALIFIED_DATA' if pending else 'SUPPORT_PENDING',
        family=family,expression=expression,independent_actionable_signals=len(independent),events=events,
        pending_reasons=pending,account_entrant=False,account_days=0,
        feature_book_sha256=book.sha256,spec_sha256=r.sha(r.SPEC.read_bytes()),
        failure_route=r.failure_route('SUPPORT_PENDING' if independent else 'WAIT_QUALIFIED_DATA'))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',type=Path,nargs='*',default=[]);parser.add_argument('--inherited',type=Path,nargs='*',default=[])
    parser.add_argument('--etf',type=Path);parser.add_argument('--at-ms',type=int,required=True)
    parser.add_argument('--context',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.out.exists():raise ValueError('preserve original screening evidence')
    book=FeatureBook(args.history,args.inherited,args.etf)
    context=json.loads(args.context.read_text()) if args.context else None
    rows={}
    for family in r.FAMILIES:
        feature=book.at(family,args.at_ms,context)
        rows[family]=dict(feature=feature,expressions=[r.alpha_expression(family,i,feature,
            dict(symbol='BTCUSDT',side='BUY')) for i in (0,1)],
            status='INFORMATION_AND_ACCOUNT_EFFECT_PENDING' if feature['status']=='FEATURE_READY' else feature['status'],
            failure_route=r.failure_route(feature['status']))
    result=dict(format='btc-nine-alpha-screen-v1',at_ms=args.at_ms,feature_book_sha256=book.sha256,
        receipt_bindings=book.bindings,spec_sha256=r.sha(r.SPEC.read_bytes()),routes=rows,
        all_families_evaluated=True,new_accounts=0,new_sessions=0,
        reason='Received values are forward research; no qualified completed new BTC intervals or historical publication vintages.',
        historical_backfill=False,orders=0,account_days=0,native_qualified=False,runtime_promoted=False)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({family:row['status'] for family,row in rows.items()}))


if __name__=='__main__':main()
