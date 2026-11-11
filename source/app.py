"""SysLinuxOS Wifi Analyzer. Copyright 2026 Franco Conidi. GPL-3.0-or-later."""

from i18n import tr

import argparse
from pathlib import Path
import sys
import time

from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt, QTimer
from PyQt5.QtGui import QBrush, QIcon, QPalette
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from controller import ScanController
from scanner import IW, parse_interfaces
from signal_dialog import SignalDialog, announce, plain_label


APP_NAME = 'SysLinuxOS Wifi Analyzer'
VERSION = Path(__file__).with_name('VERSION').read_text().strip()


class NumberItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.setData(Qt.UserRole, value)

    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)


class MainWindow(QMainWindow):
    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self.networks = {}
        self.signal_window = None
        self.controller = ScanController(demo, self)
        self.controller.scanned.connect(self.on_scan)
        self.controller.problem.connect(self.on_problem)
        self.controller.changed.connect(self.on_running)
        self.setWindowTitle(APP_NAME + (' · ' + tr('DEMO') if demo else ''))
        self.setWindowIcon(QIcon.fromTheme('syslinuxos-wifi-analyzer', QIcon.fromTheme('network-wireless')))
        self.resize(1060, 660)
        self.setMinimumSize(700, 440)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        title = plain_label(APP_NAME)
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: palette(highlight);')
        layout.addWidget(title)
        layout.addWidget(plain_label(tr('Find hidden access points · select a radio and open Signal')))
        if demo:
            banner = plain_label(tr('DEMO · simulated data, no real WiFi scanning'))
            banner.setStyleSheet('background: #fff0ce; color: #624600; padding: 8px;')
            layout.addWidget(banner)
        row = QHBoxLayout()
        label = QLabel(tr('&WiFi adapter:'))
        row.addWidget(label)
        self.interface = QComboBox()
        self.interface.setAccessibleName(tr('&WiFi adapter:').replace('&', ''))
        self.lookup = None
        label.setBuddy(self.interface)
        row.addWidget(self.interface)
        self.refresh_interfaces = QPushButton(tr('Refresh adapters'))
        self.refresh_interfaces.clicked.connect(self.load_interfaces)
        row.addWidget(self.refresh_interfaces)
        self.scan_button = QPushButton(tr('&Start scan'))
        self.scan_button.clicked.connect(self.toggle_scan)
        row.addWidget(self.scan_button)
        self.signal_button = QPushButton(tr('Si&gnal…'))
        self.signal_button.setEnabled(False)
        self.signal_button.clicked.connect(self.open_signal)
        row.addWidget(self.signal_button)
        row.addStretch()
        about = QPushButton(tr('About'))
        about.clicked.connect(self.about)
        row.addWidget(about)
        layout.addLayout(row)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr('Filter by network name or BSSID…'))
        self.filter.setAccessibleName(tr('Network filter by SSID or BSSID'))
        self.filter.textChanged.connect(self.render_table)
        layout.addWidget(self.filter)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([tr('Network / SSID'), tr('BSSID · radio'), 'MHz', tr('Channel'), 'dBm', tr('Security'), tr('Last measurement')])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 7):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.sortItems(4, Qt.DescendingOrder)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.cellDoubleClicked.connect(lambda row, col: self.open_signal())
        self.table.setAccessibleName(tr('Detected access points; each row identifies a radio'))
        layout.addWidget(self.table, 1)
        self.status = plain_label('')
        self.status.setAccessibleName(tr('Status'))
        self.status.setTextInteractionFlags(Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        self.last_problem = ''
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate: a scan is running
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(8)
        self.progress.setAccessibleName(tr('Scan in progress'))
        self.progress.hide()
        layout.addWidget(self.progress)
        layout.addWidget(plain_label(tr('Two access points may share an SSID: use the BSSID to tell them apart. The signal helps narrow down the area above the suspended ceiling.')))
        self.scan_button.setEnabled(False)
        self.load_interfaces(initial=True)
        self.age_timer = QTimer(self)
        self.age_timer.setInterval(1000)
        self.age_timer.timeout.connect(self.render_table)
        self.age_timer.start()

    def load_interfaces(self, initial=False):
        previous = self.interface.currentText()
        if self.demo:
            self.set_interfaces(['demo0'], previous, initial)
        elif not Path(IW).is_file():
            self.set_interfaces([], previous, initial)
            self.status.setText(tr('Cannot start iw. Check the installation.'))
        elif self.lookup is None:
            # Listing adapters can be slow with a misbehaving driver: never block the window.
            self.refresh_interfaces.setEnabled(False)
            self.status.setText(tr('Searching for WiFi adapters…'))
            process = self.lookup = QProcess(self)
            environment = QProcessEnvironment()
            environment.insert('PATH', '/usr/sbin:/usr/bin')
            environment.insert('LC_ALL', 'C')
            process.setProcessEnvironment(environment)
            process.setProcessChannelMode(QProcess.SeparateChannels)
            process.finished.connect(lambda *_: self.lookup_done(process, previous, initial))
            process.errorOccurred.connect(lambda *_: self.lookup_done(process, previous, initial))
            # The process is deleted once the lookup ends: only touch it while it is still the active one.
            QTimer.singleShot(5000, lambda: self.lookup is process and process.state() != QProcess.NotRunning and process.kill())
            process.start(IW, ['dev'])

    def lookup_done(self, process, previous, initial):
        if process is not self.lookup:
            return
        self.lookup = None
        names = parse_interfaces(bytes(process.readAllStandardOutput()).decode('utf-8', 'replace'))
        process.deleteLater()
        self.set_interfaces(names, previous, initial)

    def set_interfaces(self, names, previous='', initial=False):
        self.interface.clear()
        self.interface.addItems(names)
        if previous:
            self.interface.setCurrentText(previous)
        self.scan_button.setEnabled(bool(names) and not self.controller.running)
        self.refresh_interfaces.setEnabled(not self.controller.running)
        if not names:
            self.status.setText(tr('No WiFi adapter detected. Connect an adapter and refresh the list.'))
        elif initial or not self.controller.running:
            self.status.setText(tr('Ready. Start scanning to find access points.'))

    def toggle_scan(self):
        if self.controller.running:
            if self.signal_window:
                self.signal_window.close()
            self.status.setText(tr('Stopping scan…'))
            self.scan_button.setEnabled(False)
            self.controller.stop()
        else:
            if self.signal_window:
                self.signal_window.close()
            self.networks.clear()
            self.last_problem = ''
            self.render_table()
            self.status.setText(tr('Starting… confirm authorization for WiFi scanning.'))
            self.controller.start(self.interface.currentText())

    def on_running(self, running):
        self.scan_button.setText(tr('S&top scan') if running else tr('&Start scan'))
        self.scan_button.setEnabled(running or bool(self.interface.count()))
        self.interface.setEnabled(not running)
        self.refresh_interfaces.setEnabled(not running)
        self.progress.setVisible(running)
        if not running:
            self.status.setText(tr('Scan stopped. Listed measurements are historical.'))
            if self.signal_window:
                self.signal_window.invalidate(tr('Scan stopped · beeps paused'))
        self.selection_changed()

    def on_scan(self, networks, timestamp, frequency):
        for net in networks:
            # A radio that moved to another channel must not linger on the old one.
            for key in [key for key in self.networks if key[0] == net.key[0] and key != net.key]:
                del self.networks[key]
            self.networks[net.key] = (net, timestamp - net.age)
        # Bound long walking sessions without pretending old observations are new.
        cutoff = time.monotonic() - 120
        self.networks = {key: value for key, value in self.networks.items() if value[1] >= cutoff}
        self.render_table()
        mode = tr('Target channel scan · {frequency} MHz', frequency=frequency) if frequency else tr('Scanning all channels')
        self.status.setText(tr('{mode} · {count} radio in last scan' if len(networks) == 1
                               else '{mode} · {count} radios in last scan', mode=mode, count=len(networks)))
        if self.signal_window:
            self.signal_window.observe(networks, timestamp, frequency)

    def on_problem(self, message):
        self.status.setText(message)
        if message != self.last_problem:
            # Announce a new failure to assistive technology, once, not at every retry.
            self.last_problem = message
            announce(self.status)
            self.status.setFocus()
        if self.signal_window:
            self.signal_window.invalidate(message + tr(' · beeps paused'))

    def selected_key(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def selection_changed(self):
        self.signal_button.setEnabled(self.controller.running and not self.controller.stopping
                                      and self.selected_key() in self.networks)

    def render_table(self):
        query = self.filter.text().casefold()
        now = time.monotonic()
        wanted = {key: value for key, value in self.networks.items()
                  if not query or query in (value[0].ssid + ' ' + value[0].bssid).casefold()}
        table = self.table
        table.blockSignals(True)
        table.setSortingEnabled(False)
        # Update in place so the keyboard cell, selection and scroll position survive.
        for row in range(table.rowCount() - 1, -1, -1):
            if table.item(row, 0).data(Qt.UserRole) not in wanted:
                table.removeRow(row)
        rows = {table.item(row, 0).data(Qt.UserRole): row for row in range(table.rowCount())}
        for key, (net, observed) in wanted.items():
            if key not in rows:
                rows[key] = table.rowCount()
                table.insertRow(rows[key])
            self.fill_row(rows[key], net, max(0, now - observed))
        table.setSortingEnabled(True)
        table.blockSignals(False)
        self.selection_changed()

    def fill_row(self, row, net, age):
        channel = net.channel
        channel_text = '—' if not channel else (tr('{channel} (6 GHz)', channel=channel)
                                                 if net.frequency >= 5925 else str(channel))
        cells = [(net.ssid or tr('(hidden SSID)'), net.key), (net.bssid, None),
                 (str(net.frequency), net.frequency), (channel_text, channel),
                 (str(net.signal), net.signal), (tr(net.security), None),
                 (tr('{age:.0f} s ago', age=age), None)]
        stale = self.table.palette().brush(QPalette.Disabled, QPalette.Text) if age > 4 else QBrush()
        for column, (text, data) in enumerate(cells):
            item = self.table.item(row, column)
            if item is None:
                item = NumberItem(0) if column in (2, 3, 4) else QTableWidgetItem()
                self.table.setItem(row, column, item)
            item.setText(text)
            if data is not None:
                item.setData(Qt.UserRole, data)
            item.setForeground(stale)

    def open_signal(self):
        key = self.selected_key()
        if not self.controller.running or key not in self.networks:
            return
        if self.signal_window:
            if self.signal_window.network.key == key:
                self.signal_window.raise_()
                self.signal_window.activateWindow()
                return
            self.signal_window.close()
        network = self.networks[key][0]
        dialog = SignalDialog(network, self.demo, self)
        self.signal_window = dialog
        dialog.finished.connect(lambda result: self.signal_closed(dialog))
        self.controller.set_frequency(network.frequency)
        dialog.show()

    def signal_closed(self, dialog):
        if self.signal_window is dialog:
            self.signal_window = None
            self.controller.set_frequency(0)
        dialog.deleteLater()

    def about(self):
        QMessageBox.about(self, APP_NAME, f'{APP_NAME} {VERSION}\n\n' +
                          tr('Access point locator with signal gauge and audible guidance.') + '\n' +
                          'Copyright 2026 Franco Conidi · SysLinuxOS\n' +
                          tr('Parser derived from Sparrow WiFi · Copyright 2017 ghostop14') + '\n' +
                          'https://github.com/ghostop14/sparrow-wifi\n\n' +
                          tr('License GPL-3.0-or-later. No warranty.') + '\n' +
                          tr('License and credits: /usr/share/doc/syslinuxos-wifi-analyzer/'))

    def closeEvent(self, event):
        if self.signal_window:
            self.signal_window.close()
        self.controller.shutdown()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--demo', action='store_true', help=tr('Simulated data; no scanning or authorization'))
    parser.add_argument('--version', action='version', version=f'{APP_NAME} {VERSION}')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('SysLinuxOS')
    window = MainWindow(args.demo)
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
