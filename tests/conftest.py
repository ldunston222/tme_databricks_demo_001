import os
import sys


def pytest_configure():
    # Allow `import evaluator` without installing the wheel.
    repo_root = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(repo_root)
    pkg_root = os.path.join(repo_root, "ai_workflow_evaluator")
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
