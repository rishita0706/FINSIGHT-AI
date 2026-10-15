from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "finsight-ai-mvp.zip"
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".vite", "dist", "build", "coverage",
}
EXCLUDED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".joblib", ".pkl"}


def should_exclude(path: Path, output: Path) -> bool:
    if path.resolve() == output.resolve() or path.is_symlink():
        return True
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def create_archive(source_root: Path, output: Path) -> Path:
    source_root = source_root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in source_root.rglob("*")
        if path.is_file() and not should_exclude(path, output)
    )
    if not files:
        raise ValueError(f"No packageable files found under {source_root}")

    archive_root = source_root.name
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, Path(archive_root) / path.relative_to(source_root))

    validation_error = None
    with ZipFile(output) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            validation_error = f"ZIP validation failed at {corrupt_member}"
        else:
            members = set(archive.namelist())
            expected = {
                f"{archive_root}/README.md",
                f"{archive_root}/backend/.env.example",
                f"{archive_root}/frontend/.env.example",
            }
            missing = expected - members
            if missing:
                validation_error = f"ZIP is missing required project files: {sorted(missing)}"
    if validation_error:
        output.unlink(missing_ok=True)
        raise OSError(validation_error)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a clean, validated FinSight AI source ZIP.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="ZIP destination (default: artifacts/finsight-ai-mvp.zip)",
    )
    args = parser.parse_args()
    output = create_archive(ROOT, args.output)
    print(f"Created and validated {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
