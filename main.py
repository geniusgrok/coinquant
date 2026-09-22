"""The same CLI entrypoint as python -m coinquant; no legacy bot modes."""
from coinquant.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
