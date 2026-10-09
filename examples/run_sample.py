"""Run a small interpreter example from the repository root."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from optimizer.ir import parse_tac
from optimizer.analysis.interpreter import execute

program = parse_tac("""
a = 10
b = 20
c = a + b
d = c * 2
e = d + 100
t1 = a + b
t2 = a + b
unused = 50
print t2
return t2
""")

result = execute(program)

print("Output:", result.output)
print("Return value:", result.return_value)
print("Variables:", result.variables)
