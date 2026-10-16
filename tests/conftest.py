import sys
from pathlib import Path

# Ensure SUDOKU root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Pre-import ortools to ensure DLL handles are resolved before test runner hooks
try:
    import ortools
    from ortools.sat.python import cp_model
except Exception as e:
    pass
