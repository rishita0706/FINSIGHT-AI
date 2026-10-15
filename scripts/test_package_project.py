from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.package_project import create_archive


class PackageProjectTests(unittest.TestCase):
    def test_archive_keeps_sources_and_examples_but_excludes_local_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            (root / "backend").mkdir(parents=True)
            (root / "frontend").mkdir()
            (root / "README.md").write_text("Project documentation")
            (root / "frontend" / ".env.example").write_text("VITE_API_URL=local")
            (root / "frontend" / "node_modules").mkdir(parents=True)
            (root / "backend" / ".env.example").write_text("sample=true")
            (root / "backend" / ".env").write_text("secret=local")
            (root / "backend" / "finsight.db").write_bytes(b"local database")
            (root / "frontend" / "src.tsx").write_text("export {}")
            (root / "frontend" / "node_modules" / "module.js").write_text("local dependency")
            output = Path(directory) / "release.zip"

            create_archive(root, output)

            with ZipFile(output) as archive:
                members = set(archive.namelist())
                self.assertIsNone(archive.testzip())
                self.assertIn("project/backend/.env.example", members)
                self.assertIn("project/frontend/src.tsx", members)
                self.assertFalse(any(".env" in name and not name.endswith(".env.example") for name in members))
                self.assertFalse(any(name.endswith((".db", ".js")) for name in members))


if __name__ == "__main__":
    unittest.main()
