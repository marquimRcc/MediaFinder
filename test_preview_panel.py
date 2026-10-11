"""Regressões de troca rápida de prévias, sem rede nem dados do usuário."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from app.ui.preview_panel import ImageLoaderThread, PreviewPanel


class PreviewPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.files = []
        for color in ("red", "green", "blue"):
            path = str(Path(self.tmp.name) / f"{color}.png")
            image = QImage(20, 10, QImage.Format_RGB32)
            image.fill(QColor(color))
            self.assertTrue(image.save(path))
            self.files.append({"path": path, "name": color, "category": "image",
                               "extension": ".png", "size": 0, "mtime": 0})
        self.panel = PreviewPanel()
        self.release = threading.Event()

    def tearDown(self):
        self.release.set()
        self.panel._shutdown_loader()
        self.app.processEvents()
        self.panel.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        self.tmp.cleanup()

    def wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertTrue(predicate(), "A prévia não concluiu dentro do prazo")

    def delayed_run(self):
        original = ImageLoaderThread.run
        started = threading.Event()
        first = self.files[0]["path"]
        release = self.release
        def run(loader):
            if loader.target == first:
                started.set()
                release.wait(3)
            original(loader)
        return started, patch.object(ImageLoaderThread, "run", run)

    def test_rapid_selection_only_displays_latest_image(self):
        started, delayed = self.delayed_run()
        with delayed, patch.object(ImageLoaderThread, "terminate", side_effect=AssertionError("terminate proibido")):
            self.panel.set_file_data(self.files[0])
            self.assertTrue(started.wait(1))
            first_loader = self.panel._loader_thread
            for _ in range(10):
                self.panel.set_file_data(self.files[1])
                self.panel.set_file_data(self.files[2])
            self.assertIs(self.panel._loader_thread, first_loader)
            self.assertTrue(first_loader.isInterruptionRequested())
            self.release.set()
            self.wait_until(lambda: self.panel._loader_thread is None)
            pixmap = self.panel.lbl_preview.pixmap()
            self.assertFalse(pixmap.isNull())
            self.assertEqual(pixmap.toImage().pixelColor(0, 0), QColor("blue"))

    def test_reset_does_not_restore_old_image(self):
        started, delayed = self.delayed_run()
        with delayed:
            self.panel.set_file_data(self.files[0])
            self.assertTrue(started.wait(1))
            self.panel.set_file_data(self.files[1])
            self.panel.set_file_data(None)
            self.release.set()
            self.wait_until(lambda: self.panel._loader_thread is None)
            self.assertTrue(self.panel.lbl_preview.pixmap().isNull())
            self.assertEqual(self.panel.lbl_preview.text(), "Selecione um arquivo para ver a prévia")

    def test_shutdown_finishes_worker_without_starting_pending_image(self):
        started, delayed = self.delayed_run()
        with delayed:
            self.panel.set_file_data(self.files[0])
            self.assertTrue(started.wait(1))
            self.panel.set_file_data(self.files[1])
            loader = self.panel._loader_thread
            timer = threading.Timer(0.05, self.release.set)
            timer.start()
            self.panel._shutdown_loader()
            timer.join()
            self.assertFalse(loader.isRunning())
            self.app.processEvents()
            self.assertIsNone(self.panel._loader_thread)
            self.assertIsNone(self.panel._pending_image)


if __name__ == "__main__":
    unittest.main()
