import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))

from PyQt5.QtCore import QCoreApplication, QEvent, QProcess, Qt
from PyQt5.QtWidgets import QApplication
from app import MainWindow
from controller import ScanController
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
                ('en', '&Start scan', 'Si&gnal…', 'Signal lost'),
                ('it', '&Avvia scansione', 'Se&gnale…', 'Segnale perso'),
                ('fr', '&Démarrer le scan', '&Signal…', 'Signal perdu'),
                ('de', 'Scan s&tarten', '&Signal…', 'Signal verloren'),
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

    def test_table_updates_in_place_and_keeps_the_keyboard_cell(self):
        table = self.window.table
        table.setCurrentCell(1, 2)
        item = table.item(1, 2)
        before = table.rowCount()
        self.window.controller.demo_scan()
        self.window.render_table()
        self.assertEqual(table.rowCount(), before)
        self.assertEqual((table.currentRow(), table.currentColumn()), (1, 2))
        self.assertIs(table.item(1, 2), item)

    def test_radio_that_changes_channel_replaces_its_old_row(self):
        now = time.monotonic()
        self.window.on_scan([Network('02:00:00:00:00:03', 'Moved', 5180, -50)], now, 0)
        keys = [key for key in self.window.networks if key[0] == '02:00:00:00:00:03']
        self.assertEqual(keys, [('02:00:00:00:00:03', 5180)])

    def test_status_line_uses_the_singular_for_one_radio(self):
        self.window.on_scan([Network('02:00:00:00:00:09', 'One', 2412, -50)], time.monotonic(), 0)
        self.assertIn('1 radio in last scan', self.window.status.text())
        self.assertNotIn('radios', self.window.status.text())

    def test_new_problem_takes_focus_once(self):
        self.window.on_problem('Adaptateur occupé')
        self.assertEqual(self.window.last_problem, 'Adaptateur occupé')
        self.window.table.setFocus()
        self.window.on_problem('Adaptateur occupé')
        self.assertNotEqual(self.app.focusWidget(), self.window.status)

    def test_scan_indicator_and_graph_descriptions(self):
        self.assertFalse(self.window.progress.isHidden())
        self.assertTrue(self.window.progress.accessibleName())
        self.dialog.refresh()
        for graph in (self.dialog.gauge, self.dialog.history):
            self.assertTrue(graph.accessibleDescription())
            self.assertTrue(graph.focusPolicy() & Qt.TabFocus)
        self.window.toggle_scan()
        self.assertTrue(self.window.progress.isHidden())

    def test_volume_zero_is_silent(self):
        from PyQt5.QtMultimedia import QSoundEffect
        sound = Mock()
        sound.status.return_value = QSoundEffect.Ready
        beeper = self.dialog.beeper
        beeper.sound = sound
        beeper.set_volume(0)
        beeper.play()
        sound.play.assert_not_called()
        beeper.set_volume(35)
        beeper.play()
        sound.play.assert_called_once()
        beeper.sound = None

    def test_missing_iw_is_reported_not_called_no_adapter(self):
        with patch('app.Path.is_file', return_value=False):
            window = MainWindow(False)
        try:
            self.assertEqual(window.status.text(), tr('Cannot start iw. Check the installation.'))
            self.assertFalse(window.scan_button.isEnabled())
        finally:
            window.close()

    def test_adapters_are_listed_in_the_background(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory, 'iw')
            fake.write_text('#!/bin/sh\nprintf "phy#0\\n\\tInterface wlan9\\n"\n')
            fake.chmod(0o755)
            with patch('app.IW', str(fake)):
                window = MainWindow(False)
                try:
                    self.assertEqual(window.interface.count(), 0)  # nothing blocked the constructor
                    deadline = time.monotonic() + 5
                    while window.interface.count() == 0 and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                    self.assertEqual(window.interface.currentText(), 'wlan9')
                    self.assertTrue(window.scan_button.isEnabled())
                finally:
                    window.close()

    def test_lookup_timeout_after_the_lookup_ended_is_harmless(self):
        # The 5 s kill timer fires after iw finished and its QProcess was deleted.
        timers = []
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory, 'iw')
            fake.write_text('#!/bin/sh\nprintf "phy#0\\n\\tInterface wlan9\\n"\n')
            fake.chmod(0o755)
            with patch('app.IW', str(fake)), patch('app.QTimer.singleShot', lambda ms, call: timers.append(call)):
                window = MainWindow(False)
                try:
                    deadline = time.monotonic() + 5
                    while window.interface.count() == 0 and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                    self.assertTrue(timers)
                    for call in timers:
                        call()  # must not touch the deleted process
                finally:
                    window.close()


class ControllerMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def run_finish(self, code, error=None):
        controller = ScanController(False)
        messages = []
        controller.problem.connect(messages.append)
        controller.running = True
        if error:
            controller.deliver({'type': 'error', 'message': error})
        controller.finished(code, 0)
        return messages

    def test_helper_error_is_not_replaced_by_the_generic_message(self):
        messages = self.run_finish(1, 'WiFi interface unavailable')
        self.assertEqual(messages, [tr('WiFi interface unavailable')])

    def test_pkexec_exit_codes_are_distinguished(self):
        self.assertEqual(self.run_finish(126), [tr('Authorization cancelled.')])
        self.assertIn('polkit', self.run_finish(127)[0])
        self.assertIn('Authorization cancelled or helper unavailable', self.run_finish(1)[0])
        self.assertEqual(self.run_finish(0), [])

    def test_shutdown_never_waits_for_a_slow_helper(self):
        controller = ScanController(False)
        process = Mock()
        process.state.return_value = QProcess.Running
        process.waitForFinished.return_value = False
        controller.process = process
        controller.running = True
        controller.shutdown()
        self.assertLessEqual(process.waitForFinished.call_args.args[0], 2000)
        process.kill.assert_not_called()

    def test_stop_cancels_a_pending_authorization_dialog(self):
        controller = ScanController(False)
        process = Mock()
        process.state.return_value = QProcess.Running
        controller.process = process
        controller.running = True
        controller.stop()
        process.terminate.assert_called_once()
        controller.helper_started = True
        process.reset_mock()
        controller.stop()
        process.terminate.assert_not_called()

    def test_scan_events_are_capped(self):
        controller = ScanController(False)
        seen = []
        controller.scanned.connect(lambda networks, *_: seen.append(len(networks)))
        networks = [{'bssid': f'aa:bb:cc:dd:{n // 256:02x}:{n % 256:02x}', 'ssid': 'x', 'frequency': 2412,
                     'signal': -50.0, 'security': 'Open', 'age': 0.0} for n in range(700)]
        controller.deliver({'type': 'scan', 'frequency': 0, 'time': 1.0, 'networks': networks})
        self.assertEqual(seen, [500])


if __name__ == '__main__':
    unittest.main()
