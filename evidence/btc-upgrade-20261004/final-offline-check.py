"""Run the repository workflow commands once, without retries or research."""
import subprocess
import sys

package = sys.argv[1]
if package not in ('spotquant', 'coinquant'):
    raise SystemExit('unknown project')
print(sys.version, flush=True)
for argv in ([sys.executable, '-m', 'compileall', '-q', package, 'research', 'tests'],
             [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']):
    print('argv:', argv, flush=True)
    result = subprocess.run(argv)
    print('actual_exit:', result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
