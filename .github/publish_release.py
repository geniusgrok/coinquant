"""One-off GitHub Actions publisher for the measured existing 2.0.0 Release."""
import hashlib
from http.client import IncompleteRead
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

BASE = 'https://api.github.com/repos/geniusgrok/coinquant'
TARGET = '162ee7138952925ffafbc9b68be7c754c0c0a6c3'
RELEASE_ID = 407987942
BRANCH = 'release/remeasure-2.0.0-20261009'
OLD_BODY_SHA = '3c8a1e1e7b2ea326e2ec5c31341617eebb510ab538cc9c7d8b4ee90def642d68'
HEADERS = {
    'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2026-03-10',
    'Content-Type': 'application/json',
}


class NoCredentialRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


AUTH_OPENER = build_opener(NoCredentialRedirects())
WRITE_ERRORS = (RuntimeError, URLError, TimeoutError, OSError, UnicodeError,
                json.JSONDecodeError, IncompleteRead)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def api(path, method='GET', payload=None, missing_ok=False):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    try:
        with AUTH_OPENER.open(Request(BASE + path, data=data, headers=HEADERS, method=method), timeout=60) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        raise RuntimeError(f'GitHub {method} {path}: HTTP {exc.code}') from None


def matching_asset(name):
    found = [asset for asset in api(f'/releases/{RELEASE_ID}/assets?per_page=100')
             if asset['name'] == name]
    require(len(found) <= 1, 'Duplicate asset names')
    return found[0] if found else None


def verify_asset(asset, spec):
    require(asset['state'] == 'uploaded' and asset['name'] == spec['name']
            and asset['size'] == spec['bytes'], 'Release asset metadata mismatch')
    expected_url = 'https://github.com/geniusgrok/coinquant/releases/download/2.0.0/' + spec['name']
    require(asset['browser_download_url'] == expected_url, 'Unexpected asset download destination')
    if asset.get('digest') is not None:
        require(asset['digest'] == 'sha256:' + spec['sha256'], 'Release asset digest mismatch')
    # Public readback carries no repository token, including across redirects.
    actual, size = hashlib.sha256(), 0
    with urlopen(Request(expected_url, headers={'Accept': 'application/octet-stream'}), timeout=120) as response:
        while block := response.read(1024 * 1024):
            actual.update(block)
            size += len(block)
    require(size == spec['bytes'] and actual.hexdigest() == spec['sha256'], 'Release asset byte readback mismatch')
    return {'id': asset['id'], 'name': spec['name'], 'bytes': size,
            'sha256': actual.hexdigest(), 'url': expected_url}


def main():
    require(os.environ['GITHUB_REPOSITORY'] == 'geniusgrok/coinquant'
            and os.environ['GITHUB_REF'] == 'refs/heads/' + BRANCH, 'Wrong publishing context')
    metadata = api('')
    require(metadata['id'] == 1381860926 and metadata['owner']['id'] == 332557824,
            'Unexpected repository identity')
    main_before = api('/git/ref/heads/main')['object']['sha']
    tag_before = api('/git/ref/tags/2.0.0')['object']
    require(tag_before == {'sha': TARGET, 'type': 'commit', 'url': BASE + '/git/commits/' + TARGET},
            'Unexpected original release tag')
    release = api('/releases/tags/2.0.0')
    require(release['id'] == RELEASE_ID and release['target_commitish'] == TARGET
            and not release['draft'] and not release['prerelease'], 'Unexpected Release identity/status')
    title = release['name']
    body = Path('.github/release-notes-2.0.0.md').read_text(encoding='utf-8')
    manifest = json.loads(Path('.github/release-assets/manifest.json').read_text())
    require(len(body.encode()) == manifest['notes']['bytes']
            and hashlib.sha256(body.encode()).hexdigest() == manifest['notes']['sha256'], 'Notes identity mismatch')
    require(release['body'] == body or hashlib.sha256(release['body'].encode()).hexdigest() == OLD_BODY_SHA,
            'Release body changed concurrently; review before updating')
    evidence = api('/git/commits/' + manifest['evidence_commit'])
    require(evidence['tree']['sha'] == manifest['evidence_tree'], 'Measured evidence commit changed')
    require(len(manifest['assets']) == 1, 'Expected one complete public evidence asset')
    published = []
    for spec in manifest['assets']:
        require(spec['name'] == 'coinquant-2.0.0-remeasurement-evidence-20261009.tar.xz', 'Unexpected asset name')
        destination = Path(os.environ['RUNNER_TEMP']) / spec['name']
        with destination.open('xb') as output:
            for part in spec['chunks']:
                path = Path(part['path'])
                require(path.parent == Path('.github/release-assets') and path.name.startswith('part-')
                        and not path.is_symlink(), 'Unexpected asset chunk path')
                require(path.stat().st_size == part['bytes'] and sha(path) == part['sha256'], 'Asset chunk identity mismatch')
                with path.open('rb') as source:
                    while block := source.read(1024 * 1024):
                        output.write(block)
        require(destination.stat().st_size == spec['bytes'] and sha(destination) == spec['sha256'], 'Assembled asset identity mismatch')
        asset = matching_asset(spec['name'])
        if asset is None:
            upload = release['upload_url'].split('{', 1)[0]
            require(upload == f'https://uploads.github.com/repos/geniusgrok/coinquant/releases/{RELEASE_ID}/assets',
                    'Unexpected asset upload destination')
            data = destination.read_bytes()
            headers = dict(HEADERS, **{'Content-Type': 'application/x-xz', 'Content-Length': str(len(data))})
            request = Request(upload + '?' + urlencode({'name': spec['name']}), data=data, headers=headers, method='POST')
            try:
                with AUTH_OPENER.open(request, timeout=180) as response:
                    asset = json.load(response)
            except WRITE_ERRORS:
                # Reconcile an uncertain upload. Never overwrite or blindly resend.
                asset = matching_asset(spec['name'])
                if asset is None:
                    raise
            del data
        published.append(verify_asset(asset, spec))
    fresh = api('/releases/tags/2.0.0')
    require(fresh['id'] == RELEASE_ID and fresh['name'] == title and fresh['target_commitish'] == TARGET
            and not fresh['draft'] and not fresh['prerelease'], 'Release metadata changed concurrently')
    require(api('/git/ref/tags/2.0.0')['object'] == tag_before
            and api('/git/ref/heads/main')['object']['sha'] == main_before, 'Source ref changed during publication')
    # GitHub does not document an atomic compare-and-swap for this PATCH. This
    # immediate read-before-write check detects observed changes, not all races.
    if fresh['body'] != body:
        require(hashlib.sha256(fresh['body'].encode()).hexdigest() == OLD_BODY_SHA, 'Release text changed concurrently')
        try:
            api(f'/releases/{RELEASE_ID}', method='PATCH', payload={'body': body})
        except WRITE_ERRORS:
            if api('/releases/tags/2.0.0')['body'] != body:
                raise
    result = api('/releases/tags/2.0.0')
    require(result['body'].encode() == body.encode() and result['id'] == RELEASE_ID
            and result['name'] == title and result['target_commitish'] == TARGET
            and not result['draft'] and not result['prerelease'], 'Release readback mismatch')
    require(api('/git/ref/tags/2.0.0')['object'] == tag_before
            and api('/git/ref/heads/main')['object']['sha'] == main_before, 'Source ref changed')
    print(json.dumps({'release': result['html_url'], 'tag_commit': TARGET,
                      'notes_bytes': len(body.encode()), 'notes_sha256': hashlib.sha256(body.encode()).hexdigest(),
                      'evidence_commit': manifest['evidence_commit'], 'assets': published}, ensure_ascii=False))
    # Retain the publication branch as the exact payload/Actions provenance.
    # No DELETE or ref mutation is performed by this publisher.



if __name__ == '__main__':
    main()
