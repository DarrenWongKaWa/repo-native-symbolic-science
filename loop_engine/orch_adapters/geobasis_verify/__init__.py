"""Self-contained geometric-basis verification (vendored from the prototype).
Math implementations are byte-copies of the verified prototype files; only the
sys.path shims were removed. The package dir is placed on sys.path so the flat
intra-package imports (geometry, reconstruct, tshg_numeric, pilot2_v2, families)
resolve without depending on the experiment tree."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from . import core  # noqa: E402,F401
