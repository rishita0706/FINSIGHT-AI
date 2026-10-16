from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NPM = "npm.cmd" if os.name == "nt" else "npm"
CHECKS = [
    ("backend lint", [sys.executable, "-m", "ruff", "check", "app"], ROOT / "backend"),
    ("backend type check", [sys.executable, "-m", "mypy", "app/integrations/llm"], ROOT / "backend"),
    ("backend tests", [sys.executable, "-m", "pytest", "-q"], ROOT / "backend"),
    ("package tests", [sys.executable, "-m", "unittest", "scripts.test_package_project"], ROOT),
    ("frontend lint", [NPM, "run", "lint"], ROOT / "frontend"),
    ("frontend tests", [NPM, "run", "test"], ROOT / "frontend"),
    ("frontend production build", [NPM, "run", "build"], ROOT / "frontend"),
]

def main() -> None:
    for name, command, cwd in CHECKS:
        print(f"\n== {name} ==", flush=True)
        subprocess.run(command, cwd=cwd, check=True)
    print("\nAll configured checks passed.")

if __name__ == "__main__":
    main()
