"""Run audit regressions against the preserved pre-fix source or current app."""
import importlib.util
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
if "--baseline" in sys.argv:
    spec = importlib.util.spec_from_file_location("app", root / "audit/baseline/app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = module
    spec.loader.exec_module(module)
    module.app.template_folder = str(root / "audit/baseline")

if "--original" in sys.argv:
    spec = importlib.util.spec_from_file_location("baseline_tests", root / "audit/baseline/test_app.py")
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
else:
    suite = unittest.defaultTestLoader.loadTestsFromName("test_hardening")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
