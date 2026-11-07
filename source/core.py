"""WiFi observations and proximity feedback; no Qt or elevated privileges.

BSS parsing adapted from ghostop14/Sparrow WiFi wirelessengine.py (GPL-3+).
Copyright 2017 ghostop14; modifications Copyright 2026 Franco Conidi.
SPDX-License-Identifier: GPL-3.0-or-later
"""

from collections import deque
from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class Network:
    bssid: str
    ssid: str
    frequency: int
    signal: float
    security: str = 'Open'
    age: float = 0.0

    @property
    def key(self):
        return (self.bssid.lower(), self.frequency)

    @property
    def channel(self):
        return channel_for_frequency(self.frequency)


def channel_for_frequency(frequency):
    if frequency == 2484:
        return 14
    if 2412 <= frequency <= 2472:
        return (frequency - 2407) // 5
    if 4900 <= frequency < 5000:
        return (frequency - 4000) // 5
    if frequency == 5935:
        return 2
    if 5955 <= frequency <= 7115:
        return (frequency - 5950) // 5
    if 5000 <= frequency < 5935:
        return (frequency - 5000) // 5
    return 0


def decode_ssid(text):
    """Undo iw's escaping (\\xNN, \\\\) and return printable text; an unset SSID is ''."""
    raw = bytearray()
    index = 0
    while index < len(text):
        if text.startswith('\\x', index) and re.fullmatch(r'[0-9a-fA-F]{2}', text[index + 2:index + 4]):
            raw.append(int(text[index + 2:index + 4], 16))
            index += 4
        elif text.startswith('\\\\', index):
            raw.append(0x5c)
            index += 2
        else:
            raw += text[index].encode('utf-8', 'replace')
            index += 1
    ssid = raw.decode('utf-8', 'replace')
    if not ssid.strip('\x00'):
        return ''
    return ''.join(char if char.isprintable() else '?' for char in ssid)[:128]


def parse_iw(output):
    """Parse complete BSS blocks, keeping hidden SSIDs and fractional dBm.

    A missing last-seen field is accepted as age zero after a successful fresh
    scan. Known cache ages are always retained, never turned into new samples.
    Ages are relative to the helper's scan time, so the GUI turns them into its
    own clock (time.monotonic is system-wide on Linux and shared by both).
    """
    networks = []
    current = None
    section = None
    for line in output.splitlines() + ['BSS end']:
        if line.startswith('BSS '):
            if current and 'frequency' in current and 'signal' in current:
                networks.append(Network(**current))
            match = re.match(r'BSS ([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})(?:\s|\()', line)
            current = {'bssid': match[1].lower(), 'ssid': ''} if match else None
            section = None
            continue
        if current is None:
            continue
        field = line.strip()
        if field.startswith('SSID:'):
            # SSIDs are untrusted text; the UI renders them as plain text.
            current['ssid'] = decode_ssid(field[5:].lstrip())
        elif match := re.fullmatch(r'freq:\s*(\d+)(?:\.0+)?', field):
            current['frequency'] = int(match[1])
        elif match := re.fullmatch(r'signal:\s*(-?\d+(?:\.\d+)?) dBm', field):
            signal = float(match[1])
            if -120 <= signal < 0:
                current['signal'] = signal
        elif match := re.fullmatch(r'last seen:\s*(\d+) ms ago', field):
            current['age'] = int(match[1]) / 1000
        elif field.startswith('RSN:'):
            current['security'] = 'WPA2/3'
            section = 'rsn'
        elif field.startswith('WPA:'):
            section = 'wpa'
            if current.get('security') not in ('WPA2/3', 'WPA2', 'WPA3', 'OWE'):
                current['security'] = 'WPA'
        elif section == 'rsn' and (match := re.match(r'\*?\s*Authentication suites:\s*(.*)', field)):
            suites = set(match[1].split())
            if suites == {'OWE'}:
                current['security'] = 'OWE'
            elif 'SAE' in suites and 'PSK' not in suites:
                current['security'] = 'WPA3'
            elif 'PSK' in suites and 'SAE' not in suites:
                current['security'] = 'WPA2'
        elif field.startswith('capability:') and 'Privacy' in field:
            current.setdefault('security', 'WEP/Privacy')
    return networks


def beep_interval(signal, weak=-90, strong=-40):
    """Milliseconds between fixed-pitch beeps; None means silence."""
    if signal is None or not math.isfinite(signal) or not -120 <= signal < 0:
        return None
    if weak >= strong:
        raise ValueError('The weak threshold must be below the strong threshold')
    strength = max(0.0, min(1.0, (signal - weak) / (strong - weak)))
    return round(2200 * (160 / 2200) ** strength)


class SignalTracker:
    """A single BSSID/frequency, never the strongest radio sharing its SSID."""

    expiry = 4.0

    def __init__(self, key):
        self.key = key
        self.value = None
        self.raw = None
        self.peak = None
        self.last_seen = None
        self.history = deque(maxlen=90)
        self.trend = 'Waiting'

    def observe(self, networks, now):
        for net in networks:
            if (net.key != self.key or not 0 <= net.age < self.expiry
                    or beep_interval(net.signal) is None):
                continue
            observed = now - net.age
            if self.last_seen is not None and observed <= self.last_seen + 0.05:
                continue
            previous = self.value if self.fresh(now) else None
            self.value = net.signal if previous is None else previous * 0.6 + net.signal * 0.4
            self.raw = net.signal
            self.peak = net.signal if self.peak is None else max(self.peak, net.signal)
            self.last_seen = observed
            self.history.append((observed, self.value))
            delta = 0 if previous is None else self.value - previous
            self.trend = 'Increasing' if delta > 1 else 'Decreasing' if delta < -1 else 'Stable'

    def fresh(self, now):
        return self.last_seen is not None and 0 <= now - self.last_seen < self.expiry

    def interval(self, now, weak=-90, strong=-40):
        return beep_interval(self.value, weak, strong) if self.fresh(now) else None

    def reset_peak(self):
        self.peak = None
