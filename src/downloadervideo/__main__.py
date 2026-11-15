import sys
if "--worker" in sys.argv:
    from .worker import run
    raise SystemExit(run())
from .app import main
raise SystemExit(main())
