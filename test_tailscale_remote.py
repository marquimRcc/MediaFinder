import sys
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from app.core.streamer import get_local_ip, get_tailscale_ip, get_tailscale_info
from app.ui.remote_dialog import RemoteAccessDialog

class TestTailscaleRemote(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_tailscale_info_inactive(self):
        with patch("shutil.which", return_value=None), \
             patch("subprocess.run", side_effect=Exception("No tailscale")):
            info = get_tailscale_info()
            self.assertFalse(info["installed"])
            self.assertFalse(info["active"])
            self.assertIsNone(info["ip"])

    def test_tailscale_info_active(self):
        with patch("app.core.streamer.get_tailscale_ip", return_value="100.99.123.45"):
            info = get_tailscale_info()
            self.assertTrue(info["active"])
            self.assertEqual(info["ip"], "100.99.123.45")

    def test_remote_dialog_local_and_tailscale_modes(self):
        # 1. Teste em modo local padrão
        dialog = RemoteAccessDialog()
        self.assertEqual(dialog.current_mode, "local")
        self.assertTrue(dialog.local_url.startswith("http://"))
        self.assertEqual(dialog.url, dialog.local_url)
        self.assertEqual(dialog.stack.currentIndex(), 0)

        # 2. Teste alternando para Tailscale inativo
        with patch("app.ui.remote_dialog.get_tailscale_info", return_value={"installed": False, "active": False, "ip": None}):
            dialog._switch_tab("tailscale")
            self.assertEqual(dialog.current_mode, "tailscale")
            self.assertEqual(dialog.stack.currentIndex(), 1)
            self.assertEqual(dialog.stack_ts_state.currentWidget(), dialog.view_ts_setup)

        # 3. Teste alternando para Tailscale ativo
        with patch("app.ui.remote_dialog.get_tailscale_info", return_value={"installed": True, "active": True, "ip": "100.77.88.99"}):
            dialog._refresh_tailscale_state()
            self.assertEqual(dialog.stack_ts_state.currentWidget(), dialog.view_ts_active)
            self.assertEqual(dialog.txt_url_ts.text(), f"http://100.77.88.99:{dialog.port}/")
            self.assertIn("100.77.88.99", dialog.lbl_ts_badge.text())

        dialog.close()

if __name__ == "__main__":
    unittest.main()
