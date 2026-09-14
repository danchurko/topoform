"""Delivery and icon-import trust-boundary tests."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import deliver  # noqa: E402
import diagram  # noqa: E402
import import_icon  # noqa: E402


MODEL = {
    "schemaVersion": 1,
    "title": "Delivery test",
    "nodes": [{"id": "a", "label": "A"}],
    "edges": [],
}


class DeliveryTests(unittest.TestCase):
    def run_delivery(self, model: Path, output: Path, evidence: Path, browser_result):
        argv = ["deliver.py", str(model), str(output), "--evidence", str(evidence)]
        with patch.object(sys, "argv", argv), patch.object(deliver.browser_check, "run", return_value=browser_result), redirect_stdout(StringIO()) as stdout:
            return deliver.main(), json.loads(stdout.getvalue())

    def test_model_cannot_be_its_own_output(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.json"
            model.write_text(json.dumps(MODEL))
            original = model.read_bytes()
            status, report = self.run_delivery(model, model, Path(directory) / "checks", {"ok": True})
            self.assertEqual(status, 1)
            self.assertEqual(model.read_bytes(), original)
            self.assertEqual(report["existingOutput"], "not overwritten")

    def test_browser_failure_keeps_last_good_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, output = root / "model.json", root / "diagram.html"
            model.write_text(json.dumps(MODEL))
            output.write_bytes(b"last-good")
            status, report = self.run_delivery(model, output, root / "checks", {"ok": False, "errors": ["browser failed"]})
            self.assertEqual(status, 1)
            self.assertEqual(output.read_bytes(), b"last-good")
            self.assertEqual(report["existingOutput"], "not overwritten")

    def test_receipt_failure_reports_that_output_was_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, output = root / "model.json", root / "diagram.html"
            model.write_text(json.dumps(MODEL))
            output.write_bytes(b"last-good")
            original_atomic_write = diagram.atomic_write

            def fail_receipt(path, text):
                if path.name == "delivery-receipt.json":
                    raise OSError("receipt unavailable")
                return original_atomic_write(path, text)

            with patch.object(deliver.diagram, "atomic_write", side_effect=fail_receipt):
                status, report = self.run_delivery(model, output, root / "checks", {"ok": True})
            self.assertEqual(status, 1)
            self.assertNotEqual(output.read_bytes(), b"last-good")
            self.assertEqual(report["existingOutput"], "promoted; receipt write failed")


class IconImportTests(unittest.TestCase):
    def test_unsafe_source_leaves_registry_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, icons = root / "icon.svg", root / "icons"
            source.write_text('<svg viewBox="0 0 24 24"><path d="M0 0h24v24z"/></svg>')
            argv = [
                "import_icon.py", str(source), "--id", "unsafe-source",
                "--source", "https://example.org/icon.svg\nlocal", "--license", "MIT",
                "--attribution", "Example", "--icons", str(icons),
            ]
            with patch.object(sys, "argv", argv), redirect_stdout(StringIO()):
                status = import_icon.main()
            self.assertEqual(status, 1)
            self.assertFalse(icons.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
