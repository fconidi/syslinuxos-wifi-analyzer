"""Asynchronous scan session and explicitly synthetic demo. GPL-3.0-or-later."""

from i18n import scan_message, tr

from dataclasses import asdict
import json
import math
from pathlib import Path
import time

from PyQt5.QtCore import QObject, QProcess, QTimer, pyqtSignal

from core import Network


HELPER = '/usr/lib/syslinuxos-wifi-analyzer/scan-helper'


class ScanController(QObject):
    scanned = pyqtSignal(list, float, int)
    problem = pyqtSignal(str)
    changed = pyqtSignal(bool)

    def __init__(self, demo=False, parent=None):
        super().__init__(parent)
        self.demo = demo
        self.running = False
        self.stopping = False
        self.frequency = 0
        self.step = 0
        self.buffer = b''
        self.helper_started = False
        self.reported = False
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.timer = QTimer(self)
        self.timer.setInterval(750)
        self.timer.timeout.connect(self.demo_scan)

    def start(self, interface):
        if self.running:
            return
        self.stopping = False
        self.helper_started = False
        self.reported = False
        self.frequency = 0
        self.buffer = b''
        if not self.demo and not Path(HELPER).is_file():
            self.problem.emit(tr('Install the .deb package to scan. You can try --demo from source.'))
            return
        self.running = True
        self.changed.emit(True)
        if self.demo:
            self.timer.start()
            self.demo_scan()
        else:
            self.process.start('/usr/bin/pkexec', ['--disable-internal-agent', HELPER, interface])

    def set_frequency(self, frequency):
        self.frequency = frequency
        if not self.demo and self.running and not self.stopping:
            self.process.write(json.dumps({'frequency': frequency}).encode() + b'\n')

    def stop(self):
        self.stopping = True
        if self.demo:
            self.timer.stop()
            self.finished(0, QProcess.NormalExit)
        elif self.process.state() != QProcess.NotRunning:
            if not self.helper_started:
                # Still waiting for the authorization dialog: closing the pipe would not end it.
                self.process.terminate()
            self.process.write(b'{"stop":true}\n')
            self.process.closeWriteChannel()
        else:
            self.finished(0, QProcess.NormalExit)

    def shutdown(self):
        self.stop()
        if self.process.state() != QProcess.NotRunning:
            # EOF on its input ends the authorized helper by itself (an iw run in
            # progress finishes within 15 seconds). The root process cannot be
            # killed from here, so only wait briefly and never freeze the window.
            self.process.waitForFinished(1500)

    def finished(self, code, status):
        was_running = self.running
        self.running = False
        if was_running:
            self.changed.emit(False)
        if not self.stopping and code and not self.reported:
            if code == 126:
                message = tr('Authorization cancelled.')
            elif code == 127:
                message = tr('Authorization failed. Check that a polkit authentication agent is running.')
            else:
                message = tr('Scan ended. Authorization cancelled or helper unavailable.')
            self.problem.emit(message)

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.finished(1, QProcess.CrashExit)

    def read_output(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        # Helper emits bounded records; guard the UI against malformed streams.
        if len(self.buffer) > 4 * 1024 * 1024:
            self.problem.emit(tr('Scan response too large.'))
            self.stop()
            return
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                self.deliver(json.loads(line))
            except (ValueError, TypeError, KeyError):
                self.problem.emit(tr('Invalid scan response.'))
                self.stop()
                return

    def deliver(self, event):
        if self.stopping:
            return
        self.helper_started = True
        if event['type'] == 'error':
            self.reported = True
            self.problem.emit(scan_message(event['message']))
        elif event['type'] == 'scan':
            networks = [Network(**item) for item in event['networks'][:500]]
            self.scanned.emit(networks, event['time'], event['frequency'])

    def demo_scan(self):
        self.step += 1
        signal = -69 + 22 * math.sin(self.step / 10)
        nets = [Network('02:00:00:00:00:01', tr('Office · Demo'), 5180, round(signal, 1)),
                Network('02:00:00:00:00:02', tr('Office · Demo'), 2412, round(-77 + 8 * math.cos(self.step / 8), 1)),
                Network('02:00:00:00:00:03', '', 2437, -86)]
        if self.frequency:
            nets = [net for net in nets if net.frequency == self.frequency]
        self.deliver({'type': 'scan', 'frequency': self.frequency, 'time': time.monotonic(),
                      'networks': [asdict(net) for net in nets]})
