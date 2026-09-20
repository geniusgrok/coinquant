"""The same CLI entrypoint as python -m pancakequant; no legacy bot modes."""
from pancakequant.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
