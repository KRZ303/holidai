import contextlib
import importlib.util
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
VERIFY_MATRIX_PATH = ROOT_DIR / "scrape" / "verify_matrix.py"
CHROME_CONTROL_PATH = ROOT_DIR / "chrome-scrape-control" / "chrome_control.py"


def load_module(module_path: pathlib.Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    original_argv = sys.argv[:]
    try:
        sys.argv = [str(module_path)]
        spec.loader.exec_module(module)
    finally:
        sys.argv = original_argv
    return module


class FakeTimeoutProcess:
    def __init__(self):
        self.returncode = None
        self.kill_called = False
        self.communicate_calls = 0

    def communicate(self, input=None, timeout=None):
        self.communicate_calls += 1
        if self.communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="node", timeout=timeout)
        self.returncode = 124
        return ("", "timed out")

    def kill(self):
        self.kill_called = True


class VerifyMatrixGuardrailTests(unittest.TestCase):
    def setUp(self):
        self.verify_matrix = load_module(VERIFY_MATRIX_PATH, "verify_matrix_under_test")
        self.chrome_control = load_module(CHROME_CONTROL_PATH, "chrome_control_under_test")

    def test_read_csv_rows_uses_utf8_sig(self):
        csv_text = "kraj,nazwa,link,dni\nAlbania,Hotel One,https://example.com/hotel,8\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8-sig", suffix=".csv", delete=False) as handle:
            handle.write(csv_text)
            csv_path = handle.name

        try:
            fieldnames, rows = self.verify_matrix.read_csv_rows(csv_path)
        finally:
            pathlib.Path(csv_path).unlink(missing_ok=True)

        self.assertEqual(fieldnames[0], "kraj")
        self.assertEqual(rows[0]["kraj"], "Albania")
        self.assertEqual(self.verify_matrix.get_country_name(rows[0]), "Albania")

    def test_country_name_falls_back_to_legacy_headers(self):
        self.assertEqual(
            self.verify_matrix.get_country_name({"\ufeffkraj": "Albania"}),
            "Albania",
        )
        self.assertEqual(
            self.verify_matrix.get_country_name({"Destynacja": "Cyprus"}),
            "Cyprus",
        )

    def test_group_rows_by_property_keeps_same_url_with_different_names_separate(self):
        rows = [
            {
                "link": "https://www.booking.com/hotel/al/example.en-gb.html?checkin=2026-09-16",
                "nazwa": "Alpha",
            },
            {
                "link": "https://www.booking.com/hotel/al/example.en-gb.html?checkin=2026-09-18",
                "nazwa": "Alpha",
            },
            {
                "link": "https://www.booking.com/hotel/al/example.en-gb.html?checkin=2026-09-20",
                "nazwa": "Beta",
            },
        ]

        groups = self.verify_matrix.group_rows_by_property(rows)

        self.assertEqual(len(groups), 2)
        self.assertIn(
            ("https://www.booking.com/hotel/al/example.en-gb.html", "Alpha"),
            groups,
        )
        self.assertIn(
            ("https://www.booking.com/hotel/al/example.en-gb.html", "Beta"),
            groups,
        )

    def test_confirm_browser_ready_requires_exact_ok(self):
        with mock.patch("builtins.input", return_value="no"):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                ready = self.verify_matrix.confirm_booking_tab_ready()

        self.assertFalse(ready)
        self.assertIn("Type OK", stdout.getvalue())

        with mock.patch("builtins.input", return_value="OK"):
            self.assertTrue(self.verify_matrix.confirm_booking_tab_ready())

    def test_verify_matrix_eval_timeout_kills_process(self):
        proc = FakeTimeoutProcess()
        with mock.patch.object(self.verify_matrix.subprocess, "Popen", return_value=proc):
            result, err = self.verify_matrix.run_agent_browser_eval("() => 1", timeout=1)

        self.assertIsNone(result)
        self.assertIn("Timed out", err)
        self.assertTrue(proc.kill_called)

    def test_chrome_control_eval_timeout_kills_process(self):
        proc = FakeTimeoutProcess()
        with mock.patch.object(self.chrome_control.subprocess, "Popen", return_value=proc):
            result, err = self.chrome_control.run_chrome_eval("() => 1", timeout=1)

        self.assertIsNone(result)
        self.assertIn("Timed out", err)
        self.assertTrue(proc.kill_called)

    def test_ensure_browser_refuses_beta_fallback(self):
        exists_map = {
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome": False,
            "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta": True,
        }

        def fake_exists(path):
            return exists_map.get(path, False)

        with mock.patch.object(self.chrome_control, "is_port_open", return_value=False):
            with mock.patch.object(self.chrome_control.os.path, "exists", side_effect=fake_exists):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    ready = self.chrome_control.ensure_browser()

        self.assertFalse(ready)
        self.assertIn("Google Chrome was not found", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
