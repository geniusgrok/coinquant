"""Original registered serial queue plus verified public ZIP reuse before Coin jobs."""
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys

REVIEW = Path('/workspace/btc-alpha-beta-next/review')
ORIGINAL = REVIEW/'run_registered_followthrough_project_calibration.py'
ORIGINAL_SHA = '09e38e09eb755a79a8a6d7d20e83b8a371cf507e2f4c6e3b2315e13ddd9d37cd'
VAULT_SHA = '65ad132f5bf48559d455d4fa8a76966da76f661b1dda1540068f81c5f422e506'


def main():
    self_path = Path(__file__)
    self_sha = hashlib.sha256(self_path.read_bytes()).hexdigest()

    def unchanged():
        for path, expected in ((ORIGINAL, ORIGINAL_SHA), (REVIEW/'public_print_vault.py', VAULT_SHA),
                               (self_path, self_sha)):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Approved public-cache orchestration changed')

    unchanged()
    sys.path.insert(0, str(REVIEW))
    import public_print_vault as vault
    import run_registered_followthrough_project_calibration as queue
    original_run = queue.run

    def run(label, repo, module, arguments, output):
        unchanged()
        if repo == queue.ROOT/'coinquant':
            queue.source(repo)
            receipt = vault.restore(label)
            queue.source(repo)
            print('Verified public ZIP reuse receipt '+str(receipt), flush=True)
        # Exact original module, arguments, executable, output and economics.
        path = original_run(label, repo, module, arguments, output)
        unchanged()
        return path

    # Whole waiting/command chain is exclusive, including duplicate new wrappers.
    vault.require_source()
    lock_path = queue.OUT/'.registered-followthrough-exclusive.lock'
    vault.ordinary(lock_path)
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        processes = subprocess.check_output(['ps', '-eo', 'pid=,comm=,args='], text=True).splitlines()
        for line in processes:
            fields = line.strip().split(None, 2)
            if len(fields) != 3 or int(fields[0]) == os.getpid() or not fields[1].startswith('python'):
                continue
            if any(Path(arg).name.startswith('run_registered_followthrough') and arg.endswith('.py')
                   for arg in fields[2].split()):
                raise ValueError('Another registered controller is active; stop childless predecessor first')
        queue.run = run  # Orchestration only; no measured-runtime hook or monkeypatch.
        queue.main()
        unchanged()


if __name__ == '__main__':
    main()
