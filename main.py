"""The same CLI entrypoint as python -m coinquant."""
from coinquant.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
