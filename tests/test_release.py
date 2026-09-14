"""Public release/package validation seam tests."""
from pathlib import Path
import hashlib
import shutil
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release import create_archive, validate_package  # noqa: E402


class ReleaseTests(unittest.TestCase):
    def test_release_validator_accepts_the_public_package(self):
        report = validate_package(ROOT, "v1.0.0")
        self.assertTrue(report["ok"], report)

    def test_release_validator_rejects_generated_material(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "package"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            (copy / "examples" / "generated.html").write_text("<html />", encoding="utf-8")
            report = validate_package(copy)
            self.assertFalse(report["ok"])
            self.assertTrue(any(error["code"] == "FORBIDDEN_PATH" for error in report["errors"]))

    def test_release_validator_rejects_missing_readme_image(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "package"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            with (copy / "README.md").open("a", encoding="utf-8") as stream:
                stream.write('\n<img src="assets/showcases/missing.png" alt="Missing">\n')
            report = validate_package(copy)
            self.assertFalse(report["ok"])
            self.assertTrue(any(error["code"] == "README_ASSET" for error in report["errors"]))

    def test_archive_has_versioned_root_and_matching_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dist"
            report = create_archive(ROOT, output, "v1.0.0")
            archive = Path(report["archive"])
            self.assertEqual(archive.name, "topoform-1.0.0.tar.gz")
            checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(report["archiveSha256"], checksum)
            self.assertEqual((output / "SHA256SUMS").read_text(encoding="utf-8"), f"{checksum}  {archive.name}\n")
            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getnames()
            self.assertTrue(members)
            self.assertTrue(all(member.startswith("topoform-1.0.0/") for member in members))
            self.assertFalse(any("evidence/" in member or member.endswith(".html") and "/examples/" in member for member in members))

    def test_tag_must_match_skill_version(self):
        report = validate_package(ROOT, "v9.9.9")
        self.assertFalse(report["ok"])
        self.assertTrue(any(error["code"] == "TAG_VERSION" for error in report["errors"]))
