"""Walk-under-the-ceiling signal locator. SPDX-License-Identifier: GPL-3.0-or-later"""

from i18n import tr

import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                             QPushButton, QSlider, QVBoxLayout)

from audio import Beeper
from core import SignalTracker
from widgets import SignalGauge, SignalHistory


def plain_label(text=''):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    return label


class SignalDialog(QDialog):
    def __init__(self, network, demo=False, parent=None):
        super().__init__(parent)
        self.network = network
        self.tracker = SignalTracker(network.key)
        self.blocked = False
        self.setWindowTitle(tr('Signal · SysLinuxOS Wifi Analyzer'))
        self.resize(640, 720)
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        title = plain_label(tr('SIGNAL') + (' · ' + tr('DEMO') if demo else ''))
        title.setStyleSheet('font-size: 19px; font-weight: bold; color: #16618a;')
        layout.addWidget(title)
        layout.addWidget(plain_label(network.ssid or tr('Hidden SSID')))
        identity = plain_label(tr('{bssid}  ·  {frequency} MHz  ·  channel {channel}',
                                  bssid=network.bssid, frequency=network.frequency, channel=network.channel))
        identity.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(identity)
        self.gauge = SignalGauge()
        layout.addWidget(self.gauge, 3)
        self.state = plain_label(tr('Waiting for a new measurement on the target channel…'))
        self.state.setStyleSheet('font-size: 16px; font-weight: bold;')
        layout.addWidget(self.state)
        row = QHBoxLayout()
        self.details = plain_label(tr('Current: —   ·   Peak: —'))
        row.addWidget(self.details, 1)
        self.reset = QPushButton(tr('Reset peak'))
        self.reset.clicked.connect(self.tracker.reset_peak)
        row.addWidget(self.reset)
        layout.addLayout(row)
        self.history = SignalHistory()
        layout.addWidget(self.history, 1)
        row = QHBoxLayout()
        label = QLabel(tr('&Sensitivity:'))
        row.addWidget(label)
        self.sensitivity = QComboBox()
        self.sensitivity.addItem(tr('Wide search (−90 / −40 dBm)'), (-90, -40))
        self.sensitivity.addItem(tr('Near the AP (−65 / −30 dBm)'), (-65, -30))
        self.sensitivity.addItem(tr('Weak signal (−100 / −60 dBm)'), (-100, -60))
        label.setBuddy(self.sensitivity)
        row.addWidget(self.sensitivity, 1)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.audio = QCheckBox(tr('&Enable beeps'))
        row.addWidget(self.audio)
        volume_label = QLabel(tr('&Volume:'))
        row.addWidget(volume_label)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(35)
        volume_label.setBuddy(self.volume)
        self.volume.setAccessibleName(tr('Beep volume'))
        row.addWidget(self.volume, 1)
        self.test_audio = QPushButton(tr('Test audio'))
        row.addWidget(self.test_audio)
        layout.addLayout(row)
        self.audio_status = plain_label(tr('Beeps disabled · repetition speeds up as the signal grows stronger.'))
        layout.addWidget(self.audio_status)
        layout.addWidget(plain_label(tr('Walk slowly and approach from two directions. Keep height and orientation constant. The peak helps narrow down the area; it does not indicate distance or direction.')))
        close = QPushButton(tr('&Close Signal'))
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.beeper = Beeper(self)
        self.beeper.status.connect(self.audio_status.setText)
        self.audio.toggled.connect(self.beeper.set_enabled)
        self.volume.valueChanged.connect(self.beeper.set_volume)
        self.test_audio.clicked.connect(self.beeper.test)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def observe(self, networks, now, frequency):
        if frequency != self.network.frequency:
            return  # Ignore discovery or the preceding in-flight channel scan.
        previous_seen = self.tracker.last_seen
        self.tracker.observe(networks, now)
        self.blocked = self.tracker.last_seen == previous_seen
        if self.blocked:
            self.state.setText(tr('Target missing from last scan · beeps paused'))
        self.refresh()

    def invalidate(self, message):
        self.blocked = True
        self.beeper.stop()
        self.state.setText(message)
        self.refresh()

    def refresh(self):
        now = time.monotonic()
        fresh = not self.blocked and self.tracker.fresh(now)
        weak, strong = self.sensitivity.currentData()
        self.gauge.set_value(self.tracker.value if fresh else None, weak, strong)
        self.beeper.set_interval(self.tracker.interval(now, weak, strong) if fresh else None)
        if fresh:
            age = now - self.tracker.last_seen
            self.state.setText(tr('{trend} · measurement {age:.1f} s ago', trend=tr(self.tracker.trend), age=age))
        elif not self.blocked:
            self.state.setText(tr('Signal lost · beeps paused') if self.tracker.last_seen is not None
                               else tr('Waiting for a new measurement…'))
        raw = f'{self.tracker.raw:.1f} dBm' if fresh else '—'
        peak = '—' if self.tracker.peak is None else f'{self.tracker.peak:.1f} dBm'
        self.details.setText(tr('Current: {raw}   ·   Peak: {peak}', raw=raw, peak=peak))
        self.history.points = list(self.tracker.history)
        self.history.update()

    def done(self, result):
        self.timer.stop()
        self.beeper.stop()
        super().done(result)

    def closeEvent(self, event):
        self.timer.stop()
        self.beeper.stop()
        super().closeEvent(event)
