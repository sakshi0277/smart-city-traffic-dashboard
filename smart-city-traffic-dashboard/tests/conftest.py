# Makes "from src..." imports work when running pytest from the project root.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
