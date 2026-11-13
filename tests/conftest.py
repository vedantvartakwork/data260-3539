"""Ensure the repository's ``code`` package wins over Python's stdlib module.

DeepEval installs pytest plugins that import the standard-library ``code`` module
during startup. The project has historically used ``code`` as its package name,
so collection must reload the local package before homework tests are imported.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "code" / "__init__.py"

loaded = sys.modules.get("code")
if loaded is None or not hasattr(loaded, "__path__"):
    sys.modules.pop("code", None)
    spec = importlib.util.spec_from_file_location(
        "code", PACKAGE, submodule_search_locations=[str(PACKAGE.parent)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load local code package")
    module = importlib.util.module_from_spec(spec)
    sys.modules["code"] = module
    spec.loader.exec_module(module)
