"""Checks that each required library can be imported on this computer.

Run:  python scripts/check_environment.py

Each library is tested in its own separate Python process, so one
broken library cannot hide the result of the others.
It deliberately does NOT import pandas itself, so it works even when
pandas is blocked by Windows.
"""

import platform
import subprocess
import sys

# (import name, friendly name)
LIBRARIES = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("yaml", "pyyaml"),
    ("requests", "requests"),
    ("shapely", "shapely"),
    ("pyproj", "pyproj"),
    ("geopandas", "geopandas"),
    ("networkx", "networkx"),
    ("osmnx", "osmnx"),
    ("folium", "folium"),
    ("plotly", "plotly"),
    ("sklearn", "scikit-learn"),
    ("joblib", "joblib"),
    ("streamlit", "streamlit"),
    ("streamlit_folium", "streamlit-folium"),
    ("fpdf", "fpdf2"),
    ("pytest", "pytest"),
]


def check(module: str):
    code = f"import {module} as m; print(getattr(m, '__version__', 'ok'))"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    last_line = (result.stderr.strip().splitlines() or ["unknown error"])[-1]
    return False, last_line


def main() -> int:
    print(f"Python  : {sys.version.split()[0]} ({platform.architecture()[0]})")
    print(f"Platform: {platform.platform()}")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"Virtual environment active: {in_venv}")
    print("-" * 60)

    failures = []
    blocked = False
    for module, name in LIBRARIES:
        ok, info = check(module)
        if ok:
            print(f"  OK     {name:<18} {info}")
        else:
            print(f"  FAIL   {name:<18} {info}")
            failures.append(name)
            if "application control" in info.lower() or "dll load failed" in info.lower():
                blocked = True

    print("-" * 60)
    if not failures:
        print("All libraries import correctly. You are ready for Phase 2.")
        return 0

    print(f"Problem libraries: {', '.join(failures)}")
    if blocked:
        print("\nThis looks like Windows blocking a DLL / .pyd file.")
        print("Open docs/TROUBLESHOOTING_WINDOWS.md and follow Fix 1.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
