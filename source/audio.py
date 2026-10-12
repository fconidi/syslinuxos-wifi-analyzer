"""User-session sound feedback. SPDX-License-Identifier: GPL-3.0-or-later"""

from i18n import tr

from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QSoundEffect


class Beeper(QObject):
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sound = None
        self.enabled = False
        self.volume = 0.35
        self.interval = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.play)

    def prepare(self):
        if self.sound is None:
            self.sound = QSoundEffect(self)
            self.sound.statusChanged.connect(self.sound_status)
            self.sound.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name('beep.wav'))))
            self.sound.setVolume(self.volume)
            self.sound.setLoopCount(1)

    def sound_status(self):
        if self.sound.status() == QSoundEffect.Error:
            self.status.emit(tr('Audio unavailable: check the desktop audio output.'))
        elif self.sound.status() == QSoundEffect.Ready:
            self.status.emit(tr('Audio ready'))

    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.prepare()
        self.set_interval(self.interval)

    def set_volume(self, value):
        self.volume = value / 100
        if self.sound is not None:
            self.sound.setVolume(self.volume)

    def set_interval(self, interval):
        self.interval = interval
        if not self.enabled or interval is None:
            self.timer.stop()
            if self.sound is not None:
                self.sound.stop()
        elif not self.timer.isActive():
            self.timer.start(interval)
            self.play()
        elif abs(self.timer.interval() - interval) >= 20:
            self.timer.setInterval(interval)

    def play(self):
        if self.sound is not None and self.sound.status() == QSoundEffect.Ready:
            self.sound.play()

    def test(self):
        self.prepare()
        if self.sound.status() == QSoundEffect.Ready:
            self.play()
        else:
            self.status.emit(tr('Audio loading or unavailable; try the test again.'))

    def stop(self):
        self.set_interval(None)
