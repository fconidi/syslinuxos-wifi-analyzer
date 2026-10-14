import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))

from PyQt5.QtWidgets import QApplication
from app import MainWindow
from core import Network
from i18n import tr


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(True)
        self.window.show()
        self.window.toggle_scan()
        self.window.table.selectRow(0)
        self.window.open_signal()
        self.dialog = self.window.signal_window
        self.window.controller.demo_scan()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_demo_preserves_two_radios_and_locks_frequency(self):
        self.assertEqual(self.window.table.rowCount(), 3)
        self.assertIn(tr('DEMO'), self.window.windowTitle())
        self.assertIsNotNone(self.dialog.tracker.value)
        self.assertEqual(self.window.controller.frequency, self.dialog.network.frequency)
        self.assertEqual(self.window.controller.process.state(), 0)
        self.assertFalse(self.dialog.audio.isChecked())
        self.assertIsNone(self.dialog.beeper.sound)

    def test_error_and_missing_target_cannot_resume_old_beeps(self):
        self.dialog.beeper.enabled = True  # Exercise cadence without a real audio device.
        self.dialog.refresh()
        self.assertTrue(self.dialog.beeper.timer.isActive())
        self.window.on_problem('Scheda occupata')
        self.assertFalse(self.dialog.beeper.timer.isActive())
        self.assertIsNone(self.dialog.gauge.value)
        other = Network('02:00:00:00:ff:01', 'Other', self.dialog.network.frequency, -30)
        self.dialog.observe([other], time.monotonic(), self.dialog.network.frequency)
        self.assertFalse(self.dialog.beeper.timer.isActive())
        self.assertIsNone(self.dialog.gauge.value)

    def test_freshness_expiry_silences_and_clears_gauge(self):
        self.dialog.beeper.enabled = True
        self.dialog.tracker.last_seen = time.monotonic() - 5
        self.dialog.refresh()
        self.assertIsNone(self.dialog.gauge.value)
        self.assertFalse(self.dialog.beeper.timer.isActive())
        self.assertEqual(tr('Signal lost · beeps paused'), self.dialog.state.text())

    def test_dialog_close_stops_feedback_and_restores_discovery(self):
        self.dialog.beeper.enabled = True
        self.dialog.refresh()
        self.assertTrue(self.dialog.beeper.timer.isActive())
        self.dialog.close()
        self.assertFalse(self.dialog.beeper.timer.isActive())
        self.assertFalse(self.dialog.timer.isActive())
        self.assertIsNone(self.window.signal_window)
        self.assertEqual(self.window.controller.frequency, 0)

    def test_stopping_scanning_closes_tracking_and_demo_timer(self):
        self.window.toggle_scan()
        self.assertIsNone(self.window.signal_window)
        self.assertFalse(self.window.controller.running)
        self.assertFalse(self.window.controller.timer.isActive())
        self.assertFalse(self.window.signal_button.isEnabled())

    def test_filter_and_refresh_preserve_radio_selection(self):
        key = self.window.selected_key()
        self.window.render_table()
        self.assertEqual(self.window.selected_key(), key)
        self.window.filter.setText('00:00:00:00:02')
        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertEqual(self.dialog.network.key, key)

    def test_all_languages_translate_discovery_tracking_and_errors(self):
        for language, scan, signal, lost in [
                ('en', '&Start scan', '&Signal…', 'Signal lost'),
                ('it', '&Avvia scansione', '&Segnale…', 'Segnale perso'),
                ('fr', '&Démarrer le scan', '&Signal…', 'Signal perdu'),
                ('de', '&Scan starten', '&Signal…', 'Signal verloren'),
                ('es', '&Iniciar escaneo', '&Señal…', 'Señal perdida')]:
            with self.subTest(language=language), patch.dict(os.environ, {'LANG': language}, clear=True):
                window = MainWindow(True)
                try:
                    window.show()
                    self.assertEqual(window.scan_button.text(), scan)
                    self.assertEqual(window.signal_button.text(), signal)
                    window.toggle_scan()
                    window.table.selectRow(0)
                    window.open_signal()
                    window.controller.demo_scan()
                    dialog = window.signal_window
                    self.assertIsNotNone(dialog.gauge.value)
                    self.assertIn(tr('Stable'), dialog.state.text())
                    dialog.tracker.last_seen = time.monotonic() - 5
                    dialog.refresh()
                    self.assertIn(lost, dialog.state.text())
                    window.controller.deliver({'type': 'error',
                                              'message': 'Adapter busy: waiting before retrying.'})
                    self.assertEqual(window.status.text(), tr('Adapter busy: waiting before retrying.'))
                    self.assertFalse(dialog.beeper.timer.isActive())
                    self.app.processEvents()
                finally:
                    window.close()


if __name__ == '__main__':
    unittest.main()
