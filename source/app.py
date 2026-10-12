"""SysLinuxOS Wifi Analyzer. Copyright 2026 Franco Conidi. GPL-3.0-or-later."""

from i18n import tr

import argparse
from pathlib import Path
import sys
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from controller import ScanController
from scanner import wireless_interfaces
from signal_dialog import SignalDialog, plain_label


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
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: #16618a;')
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
        self.interface.addItems(['demo0'] if demo else wireless_interfaces())
        label.setBuddy(self.interface)
        row.addWidget(self.interface)
        self.refresh_interfaces = QPushButton(tr('Refresh adapters'))
        self.refresh_interfaces.clicked.connect(self.load_interfaces)
        row.addWidget(self.refresh_interfaces)
        self.scan_button = QPushButton(tr('&Start scan'))
        self.scan_button.clicked.connect(self.toggle_scan)
        row.addWidget(self.scan_button)
        self.signal_button = QPushButton(tr('&Signal…'))
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
        self.status = plain_label(tr('Ready. Start scanning to find access points.') if self.interface.count()
                                  else tr('No WiFi adapter detected. Connect an adapter and refresh the list.'))
        layout.addWidget(self.status)
        layout.addWidget(plain_label(tr('Two access points may share an SSID: use the BSSID to tell them apart. The signal helps narrow down the area above the suspended ceiling.')))
        self.scan_button.setEnabled(bool(self.interface.count()))
        self.age_timer = QTimer(self)
        self.age_timer.setInterval(1000)
        self.age_timer.timeout.connect(self.render_table)
        self.age_timer.start()

    def load_interfaces(self):
        previous = self.interface.currentText()
        self.interface.clear()
        self.interface.addItems(['demo0'] if self.demo else wireless_interfaces())
        if previous:
            self.interface.setCurrentText(previous)
        self.scan_button.setEnabled(bool(self.interface.count()))
        if not self.interface.count():
            self.status.setText(tr('No WiFi adapter detected. Check the connection and driver.'))

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
            self.render_table()
            self.status.setText(tr('Starting… confirm authorization for WiFi scanning.'))
            self.controller.start(self.interface.currentText())

    def on_running(self, running):
        self.scan_button.setText(tr('S&top scan') if running else tr('&Start scan'))
        self.scan_button.setEnabled(running or bool(self.interface.count()))
        self.interface.setEnabled(not running)
        self.refresh_interfaces.setEnabled(not running)
        if not running:
            self.status.setText(tr('Scan stopped. Listed measurements are historical.'))
            if self.signal_window:
                self.signal_window.invalidate(tr('Scan stopped · beeps paused'))
        self.selection_changed()

    def on_scan(self, networks, timestamp, frequency):
        for net in networks:
            self.networks[net.key] = (net, timestamp - net.age)
        # Bound long walking sessions without pretending old observations are new.
        cutoff = time.monotonic() - 120
        self.networks = {key: value for key, value in self.networks.items() if value[1] >= cutoff}
        self.render_table()
        mode = tr('Target channel scan · {frequency} MHz', frequency=frequency) if frequency else tr('Scanning all channels')
        self.status.setText(tr('{mode} · {count} radios in last scan', mode=mode, count=len(networks)))
        if self.signal_window:
            self.signal_window.observe(networks, timestamp, frequency)

    def on_problem(self, message):
        self.status.setText(message)
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
        selected = self.selected_key()
        query = self.filter.text().casefold()
        now = time.monotonic()
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for net, observed in self.networks.values():
            if query and query not in (net.ssid + ' ' + net.bssid).casefold():
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = QTableWidgetItem(net.ssid or tr('(hidden SSID)'))
            name.setData(Qt.UserRole, net.key)
            age = max(0, now - observed)
            items = [name, QTableWidgetItem(net.bssid), NumberItem(net.frequency), NumberItem(net.channel),
                     NumberItem(net.signal), QTableWidgetItem(tr(net.security)), QTableWidgetItem(tr('{age:.0f} s ago', age=age))]
            for column, item in enumerate(items):
                if age > 4:
                    item.setForeground(QColor('#687581'))
                self.table.setItem(row, column, item)
        self.table.setSortingEnabled(True)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.UserRole) == selected:
                self.table.selectRow(row)
                break
        self.table.blockSignals(False)
        self.selection_changed()

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
