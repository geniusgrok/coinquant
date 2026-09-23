"""Join saved PIR1 child calls to actual filled campaign ownership and exits."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path


def records(path):
    with gzip.open(path, 'rt') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(attribution, candidate, control):
    children = json.loads(attribution.read_text())['children']
    decisions_path = candidate/'decisions.csv.gz'
    orders_path = candidate/'orders.csv.gz'
    execution_path = candidate/'execution.jsonl'
    decisions = {int(row['time']): row for row in records(decisions_path)}
    control_decisions = {int(row['time']): row for row in records(control/'decisions.csv.gz')}
    orders = records(orders_path)
    events = [json.loads(line) for line in execution_path.read_text().splitlines()]
    mothers = {row['parent_id']: row for row in events if row['kind']=='mother_created'}
    fills = sorted((row['time'], mothers[row['parent_id']]['campaign'])
                   for row in events if row['kind']=='child' and row.get('event')=='entry')
    found = []
    for child in children:
        for call_time in child['active_call_times']:
            row = decisions[call_time]
            if not float(row['quantity']):
                continue
            owner = next((campaign for time, campaign in reversed(fills) if time<call_time), None)
            if owner == child['identity']:
                continue
            if owner is None or row['action']!='hold' or child['parent_invalidation_time']>=call_time:
                raise ValueError('saved child signal, owner and call do not support the hold diagnosis')
            flat = next((order for order in orders if int(order['time'])>=call_time
                         and float(order['quantity_after'])==0), None)
            found.append(dict(call_time=call_time, child_identity=child['identity'],
                              child_parent=child['parent_identity'], held_campaign=owner,
                              parent_invalidated_at=child['parent_invalidation_time'],
                              quantity_at_call=row['quantity'], actual_action=row['action'],
                              corrected_action='exit', control_action=control_decisions[call_time]['action'],
                              first_flat_time=int(flat['time']) if flat else None,
                              first_flat_event=flat['event'] if flat else None,
                              exposure_extension_hours=(int(flat['time'])-call_time)/3600000 if flat else None))
    if len(found)!=13 or len({row['held_campaign'] for row in found})!=9:
        raise ValueError('saved account no longer matches the pre-result branch audit')
    return dict(status='saved_original_PIR1_semantics_audit', calls=len(found),
                affected_campaigns=len({row['held_campaign'] for row in found}), rows=found,
                input_sha256={str(path.name):digest(path) for path in
                              (attribution,decisions_path,orders_path,execution_path)})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--attribution',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--control',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    a.output.write_text(json.dumps(audit(a.attribution,a.candidate,a.control),indent=2)+'\n')
