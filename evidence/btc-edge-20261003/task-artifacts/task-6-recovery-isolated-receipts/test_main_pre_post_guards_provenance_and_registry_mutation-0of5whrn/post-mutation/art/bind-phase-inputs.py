"""Bind an actual assessor export to one phase of an immutable parent freeze.

No producer, source freeze, export generation, profile rewrite, or account action.
The source-bound edge_assessment interface validates project/spec/profile/raw links.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ART = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('controller', ART / 'run-registered-phase.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
sha, write_new = controller.sha, controller.write_new


def require(value, message):
    if not value:
        raise ValueError(message)


def binding(path):
    path = Path(path).absolute()
    require(not path.is_symlink(), 'original binding cannot be a symlink')
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def assessor(freeze):
    repo = freeze['projects']['spot']['repository']
    sys.path.insert(0, repo)
    from research import edge_assessment
    require(Path(edge_assessment.__file__).resolve() == Path(repo) / 'research/edge_assessment.py',
            'assessor import differs from frozen source')
    return edge_assessment


def validate_report(report, freeze, interface):
    require(report['format'] == 'btc-edge-assessment-v1' and not report['blocking'] and
            not report['rejected_files'], 'actual nonblocking assessor report required')
    require(report['analysis_source'] == freeze['projects']['spot']['source'], 'assessor source differs from parent')
    for kind in ('spot', 'perp'):
        require(report['contracts'][kind] == dict(spec_sha256=interface.SPEC_HASH[kind],
                protocol_sha256=interface.PROTOCOL_HASH[kind]), 'assessor contract mismatch')
    # Calibration begins only after the entire original unscaled inventory was audited.
    unscaled = {key for key in interface.required_matrix() if key.endswith('|0|unscaled') and
                key.split('|')[3] == '1E+4'}
    require(unscaled, 'actual assessor unscaled inventory missing')
    raw = {}
    for key in unscaled | set(report['accounts']):
        account = report['accounts'].get(key)
        require(account is not None and account['status'] == 'complete' and not account['reasons'] and
                isinstance(account.get('monetary_audit'), dict) and
                account['monetary_audit'].get('passed') is True, 'complete audited account required: ' + key)
        kind = account['kind']
        require(account['source'] == freeze['projects'][kind]['source'], 'raw account source differs from parent')
        item = binding(account['path'])
        require(item['sha256'] == account['raw_sha256'] == report['inputs'][account['path']], 'actual raw account byte mismatch')
        raw[item['path']] = item
    return list(raw.values())


def validate_export(report, document, kind, label, freeze, interface):
    names = [interface.BASE[kind], *interface.ORDER[kind]]
    require(label in (kind, kind + '_combo'), 'unknown assessor export label')
    if label.endswith('_combo'):
        parts = report['combinations'][kind]
        require(parts == [n for n in interface.ORDER[kind] if report['decisions'][kind][n]['eligible']] and len(parts) >= 2,
                'combo must include ALL eligible singles in registered order')
        names.append(interface.combo_name(kind, parts))
    interface.validate_profile_document(document, kind, names)
    require(document == report['calibration_documents'][label], 'export differs from actual assessor report')
    for name, profile in document['profiles'].items():
        account = report['accounts'][interface.account_id(kind, name)]
        diagnostics = report['calibration_diagnostics'][label][name]
        require(account['status'] == 'complete' and account['source'] == freeze['projects'][kind]['source'] and
                profile['base_bundle_sha256'] == account['raw_sha256'] == diagnostics['raw_sha256'] and
                diagnostics['source'] == account['source'] and diagnostics['training_days'] == 731,
                'profile original audited raw/source/training mismatch')


def validate_supplement(registry, freeze_sha, freeze):
    require(registry['format'] == 'btc-edge-conditional-registration-v1' and
            registry['parent_freeze_sha256'] == freeze_sha and
            registry['parent_registry_sha256'] == controller.REGISTRY_SHA, 'supplement parent mismatch')
    controller.verify_files(registry['bound_files'])
    report_binding = registry['assessment_report']
    require(report_binding in registry['bound_files'], 'supplement report must be bound')
    report = json.loads(Path(report_binding['path']).read_bytes())
    api = assessor(freeze)
    raw_accounts = validate_report(report, freeze, api)
    require(all(item in registry['bound_files'] for item in raw_accounts), 'supplement must retain original raw account bindings')
    require(registry['condition'] in ('all-eligible-combination', 'selected-budgets'), 'unregistered condition')
    kind = registry['project_kind']
    parts = report['combinations'].get(kind, [])
    selected = report['selected'][kind]
    if registry['condition'] == 'all-eligible-combination':
        require(parts == [n for n in api.ORDER[kind] if report['decisions'][kind][n]['eligible']] and len(parts) >= 2 and
                all(report['decisions'][kind][n]['status'] == 'complete' for n in api.ORDER[kind]), 'inapplicable/subset combination')
        candidate = api.combo_name(kind, parts)
        role = registry['role']
        require(role in ('unscaled', 'risk'), 'invalid combination role')
        expected = {(s, '10000', role == 'risk') for s in (['base'] if role == 'risk' else api.STRESSES[kind])}
    else:
        best, eligible_parts = api.choose_singles(kind, {n: report['decisions'][kind][n] for n in api.ORDER[kind]})
        expected_selected = api.combo_name(kind, eligible_parts) if eligible_parts and report['decisions'][kind].get(api.combo_name(kind, eligible_parts), {}).get('eligible') else best
        require(all(report['decisions'][kind][n]['status'] == 'complete' for n in api.ORDER[kind]) and
                (not eligible_parts or report['decisions'][kind].get(api.combo_name(kind, eligible_parts), {}).get('status') == 'complete') and
                selected == expected_selected, 'selection must follow complete original ALL-eligible decision rule')
        require(selected != api.BASE[kind] and report['decisions'][kind][selected]['eligible'] and
                report['decisions'][kind][selected]['status'] == 'complete', 'selected-budget condition incomplete')
        candidate = selected
        expected = {('base', str(capital), False) for capital in (2500, 5000, 7500)}
    original = json.loads(controller.REGISTRY.read_bytes())['jobs']
    exemplar = next(j for j in original if j['project_kind'] == kind)
    original_outputs = {j['output'] for j in original}
    actual = set()
    allowed = {'--candidate', '--combo', '--scenario', '--initial-cny', '--risk-calibration', '--features', '--out', '--prints'}
    output_root = Path(exemplar['output']).parent.parent
    for job in registry['jobs']:
        require(job['project_kind'] == kind and job['cwd'] == freeze['projects'][kind]['repository'] and
                job['phase'] == registry['phase'] and job['expected_accounts'] == 1, 'conditional project/phase/account mismatch')
        command = job['command']
        require(command[:4] == exemplar['command'][:4], 'only registered research entrypoint allowed')
        values, i = {}, 4
        while i < len(command):
            option = command[i]
            require(option not in values, 'duplicate option')
            if option == '--restore-prints' and kind == 'perp':
                values[option] = True
                i += 1
            else:
                require(option in allowed and i + 1 < len(command), 'unregistered conditional option')
                values[option] = command[i + 1]
                i += 2
        combo = candidate == api.combo_name(kind, parts) if len(parts) >= 2 else False
        if combo:
            require(values.get('--combo') == ','.join(parts), 'conditional combo differs from ALL eligible')
            require(values.get('--candidate') == 'combo' if kind == 'spot' else '--candidate' not in values,
                    'invalid combo CLI identity')
        else:
            require(values.get('--candidate') == candidate and '--combo' not in values, 'selected candidate mismatch')
        feature = exemplar['command'][exemplar['command'].index('--features') + 1]
        require(values.get('--features') == feature and values.get('--out') == job['output'], 'conditional feature/output mismatch')
        output = Path(job['output'])
        require(output.is_absolute() and output_root in output.parents and '..' not in output.parts and
                job['output'] not in original_outputs, 'conditional output must be new within task output tree')
        require('--prints' not in values if kind == 'spot' else values.get('--restore-prints') is True and
                Path(values.get('--prints', '')).parent == output_root / 'print-cache', 'conditional print cache scope')
        actual.add((values.get('--scenario'), values.get('--initial-cny', '10000'), '--risk-calibration' in values))
    require(actual == expected and len(registry['jobs']) == len(expected), 'conditional complete inventory required')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('freeze', 'report', 'export', 'production-profile', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--kind', required=True, choices=('spot', 'perp'))
    parser.add_argument('--phase', required=True)
    parser.add_argument('--export-label', required=True)
    parser.add_argument('--registry', type=Path, default=controller.REGISTRY)
    parser.add_argument('--registry-sha256', default=controller.REGISTRY_SHA)
    args = parser.parse_args(argv)
    freeze_binding = binding(args.freeze)
    freeze = json.loads(args.freeze.read_bytes())
    require(json.loads((ART/'controller-parent-freeze.json').read_bytes()) == freeze_binding,
            'phase requires the exclusive original parent anchor')
    require(freeze['controller_root'] == str(ART), 'parent controller root mismatch')
    require(sha(controller.REGISTRY) == controller.REGISTRY_SHA and sha(args.registry) == args.registry_sha256,
            'registry SHA mismatch')
    jobs = json.loads(args.registry.read_bytes())['jobs']
    matching = [j for j in jobs if j['phase'] == args.phase and j['project_kind'] == args.kind]
    profiles = {j['command'][j['command'].index('--risk-calibration')+1] for j in matching if '--risk-calibration' in j['command']}
    require(matching and profiles == {str(args.production_profile.absolute())}, 'exact registered production profile required')
    # Assessor lives in Spot even when exporting a Coin profile.
    for kind in {'spot', args.kind}:
        controller.guard(dict(project_kind=kind, cwd=freeze['projects'][kind]['repository']), freeze)
    report_file, export_file, production = binding(args.report), binding(args.export), binding(args.production_profile)
    report = json.loads(args.report.read_bytes())
    document = json.loads(args.export.read_bytes())
    api = assessor(freeze)
    raw = validate_report(report, freeze, api)
    validate_export(report, document, args.kind, args.export_label, freeze, api)
    command = report['command']
    require(command[1:3] == ['-m', 'research.edge_assessment'] and '--calibration-out-dir' in command,
            'actual assessor export command required')
    original_path = Path(command[command.index('--calibration-out-dir')+1]) / (args.export_label + '.json')
    require(original_path.absolute() == args.export.absolute() and
            Path(command[command.index('--out')+1]).absolute() == args.report.absolute(), 'original assessor report/export path mismatch')
    require(export_file['sha256'] == production['sha256'] and export_file['bytes'] == production['bytes'],
            'production profile must have identical ORIGINAL export bytes')
    bound = list({item['path']: item for item in [freeze_binding, report_file, export_file, production, *raw]}.values())
    body = dict(format='btc-edge-phase-input-binding-v1', created_utc=controller.now(),
                parent_freeze_sha256=freeze_binding['sha256'], project_kind=args.kind, phase=args.phase,
                registry_sha256=args.registry_sha256, analysis_source=report['analysis_source'],
                export_label=args.export_label, assessor_report=report_file, original_export=export_file,
                production_profile=production, bound_files=bound)
    controller.verify_files(bound)
    for kind in {'spot', args.kind}:
        controller.guard(dict(project_kind=kind, cwd=freeze['projects'][kind]['repository']), freeze)
    require(sha(args.freeze) == freeze_binding['sha256'], 'parent freeze mutated during phase binding')
    write_new(args.out, body)
    print(json.dumps(dict(output=str(args.out), sha256=sha(args.out))))


if __name__ == '__main__':
    main()
