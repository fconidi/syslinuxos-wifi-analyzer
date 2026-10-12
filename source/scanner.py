"""Restricted iw scanning backend. SPDX-License-Identifier: GPL-3.0-or-later"""

from dataclasses import asdict
import json
import os
import re
import select
import subprocess
import sys
import time

from core import parse_iw


IW = '/usr/sbin/iw'


def validate_interface(interface):
    if not isinstance(interface, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,14}', interface):
        raise ValueError('Invalid WiFi interface')
    return interface


def validate_frequency(frequency):
    if type(frequency) is not int or (frequency != 0 and not 2300 <= frequency <= 7125):
        raise ValueError('Invalid WiFi frequency')
    return frequency


def scan_command(interface, frequency):
    command = [IW, 'dev', validate_interface(interface), 'scan']
    if validate_frequency(frequency):
        command += ['freq', str(frequency)]
    return command + ['flush']


def parse_command(line):
    try:
        command = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('Invalid command') from exc
    if command == {'stop': True}:
        return 'stop'
    if not isinstance(command, dict) or set(command) != {'frequency'}:
        raise ValueError('Command not allowed')
    return validate_frequency(command['frequency'])


def wireless_interfaces():
    try:
        result = subprocess.run([IW, 'dev'], capture_output=True, text=True, timeout=5,
                                env={'PATH': '/usr/sbin:/usr/bin', 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired):
        return []
    return re.findall(r'^\s*Interface ([a-zA-Z0-9][a-zA-Z0-9_.-]{0,14})\s*$', result.stdout, re.M)


def scan_once(interface, frequency):
    command = scan_command(interface, frequency)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                encoding='utf-8', errors='replace',
                                env={'PATH': '/usr/sbin:/usr/bin', 'LC_ALL': 'C'})
    except subprocess.TimeoutExpired:
        return {'type': 'error', 'message': 'Scan timed out. Check the WiFi adapter and driver.'}
    except OSError:
        return {'type': 'error', 'message': 'Cannot start iw. Check the installation.'}
    if result.returncode:
        details = (result.stderr or result.stdout).strip()[:300]
        if 'busy' in details.lower():
            message = 'Adapter busy: waiting before retrying.'
        elif 'down' in details.lower() or 'rfkill' in details.lower():
            message = 'WiFi disabled or blocked. Enable it in network settings.'
        else:
            message = 'Scan failed: ' + details
        return {'type': 'error', 'message': message}
    return {'type': 'scan', 'frequency': frequency, 'time': time.monotonic(),
            'networks': [asdict(net) for net in parse_iw(result.stdout)]}


def emit(event):
    print(json.dumps(event, ensure_ascii=True), flush=True)


def helper_main():
    """One authorized session. EOF or stop ends it; no arbitrary operations.

    Commands are read as bounded bytes to avoid text-buffer/select interactions.
    During iw, shutdown waits at most the subprocess timeout (15 seconds).
    """
    if len(sys.argv) != 2 or os.geteuid() != 0:
        emit({'type': 'error', 'message': 'Start scanning from the installed app.'})
        return 1
    try:
        interface = validate_interface(sys.argv[1])
        if interface not in wireless_interfaces():
            raise ValueError('WiFi interface unavailable')
        frequency = 0
        buffer = b''
        next_scan = time.monotonic()
        while True:
            wait = max(0.0, next_scan - time.monotonic())
            if select.select([sys.stdin], [], [], wait)[0]:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data:
                    return 0
                buffer += data
                if len(buffer) > 4096:
                    raise ValueError('Command too long')
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    value = parse_command(line)
                    if value == 'stop':
                        return 0
                    frequency = value
                    next_scan = time.monotonic()
            if time.monotonic() >= next_scan:
                event = scan_once(interface, frequency)
                emit(event)
                next_scan = time.monotonic() + (1.5 if event['type'] == 'error' else 0.5)
    except (ValueError, OSError) as exc:
        if not isinstance(exc, BrokenPipeError):
            try:
                emit({'type': 'error', 'message': str(exc)})
            except BrokenPipeError:
                pass
        return 1
