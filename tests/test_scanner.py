import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import scanner
from scanner import scan_command, scan_once, validate_interface, parse_command


class ScannerTests(unittest.TestCase):
    def test_only_interface_names_are_accepted(self):
        for name in ['wlan0', 'wlx001122aabbcc', 'wlp2s0']:
            self.assertEqual(validate_interface(name), name)
        for name in ['', '-help', '../wlan0', 'wlan0;id', 'wlan0\n', 'a' * 16]:
            with self.assertRaises(ValueError):
                validate_interface(name)

    def test_scan_arguments_flush_cache_and_have_no_shell(self):
        self.assertEqual(scan_command('wlan0', 5180),
                         ['/usr/sbin/iw', 'dev', 'wlan0', 'scan', 'freq', '5180', 'flush'])
        for frequency in [-1, 1, 99999, '2412;id', True, 2412.5]:
            with self.assertRaises(ValueError):
                scan_command('wlan0', frequency)

    def test_protocol_accepts_only_mode_changes_and_stop(self):
        self.assertEqual(parse_command(b'{"frequency":2412}'), 2412)
        self.assertEqual(parse_command(b'{"frequency":0}'), 0)
        self.assertEqual(parse_command(b'{"stop":true}'), 'stop')
        for value in [b'[]', b'{"exec":"id"}', b'{"frequency":0,"exec":"id"}', b'{"frequency":true}', b'garbage']:
            with self.assertRaises(ValueError):
                parse_command(value)

    @patch('scanner.subprocess.run')
    def test_failed_scan_is_error_not_empty_success(self, run):
        run.return_value = subprocess.CompletedProcess([], 240, '', 'Device or resource busy (-16)')
        result = scan_once('wlan0', 2412)
        self.assertEqual(result['type'], 'error')
        self.assertEqual('Adapter busy: waiting before retrying.', result['message'])
        self.assertNotIn('networks', result)
        self.assertEqual(run.call_args.kwargs['timeout'], 15)

    @patch('scanner.subprocess.run')
    def test_a_beacon_flood_is_capped_to_the_strongest_radios(self, run):
        output = ''.join(f'BSS aa:bb:cc:{n // 256:02x}:{n % 256:02x}:01(on wlan0)\n\tfreq: 2412\n'
                         f'\tsignal: -{30 + n % 60}.00 dBm\n\tSSID: s{n}\n' for n in range(900))
        run.return_value = subprocess.CompletedProcess([], 0, output, '')
        networks = scan_once('wlan0', 0)['networks']
        self.assertEqual(len(networks), scanner.MAX_NETWORKS)
        self.assertEqual(networks[0]['signal'], -30.0)
        self.assertEqual(networks, sorted(networks, key=lambda net: -net['signal']))

    def test_nested_json_command_is_rejected_cleanly(self):
        with self.assertRaises(ValueError):
            parse_command(b'[' * 5000)

    def test_interface_listing_is_parsed(self):
        self.assertEqual(scanner.parse_interfaces('phy#0\n\tInterface wlan0\n\tInterface p2p-dev-wlan0\n'),
                         ['wlan0', 'p2p-dev-wlan0'])

    def run_helper(self, stdin_bytes=b'', events=None, uid=0, argv=('scan-helper', 'wlan0'), after=None):
        emitted = []
        read, write = os.pipe()
        os.write(write, stdin_bytes)
        if after is not None:
            after(write)
        else:
            os.close(write)
        with os.fdopen(read, 'rb', buffering=0) as stdin, \
                patch.object(scanner.sys, 'argv', list(argv)), \
                patch.object(scanner.sys, 'stdin', stdin), \
                patch.object(scanner.os, 'geteuid', return_value=uid), \
                patch.object(scanner, 'emit', emitted.append), \
                patch.object(scanner, 'wireless_interfaces', return_value=['wlan0']), \
                patch.object(scanner, 'ERROR_DELAY', 0), \
                patch.object(scanner, 'scan_once', side_effect=events):
            return scanner.helper_main(), emitted

    def test_helper_refuses_to_run_unprivileged_or_with_bad_arguments(self):
        for kwargs in ({'uid': 1000}, {'argv': ('scan-helper',)}, {'argv': ('scan-helper', 'wlan0', 'x')}):
            status, emitted = self.run_helper(**kwargs)
            self.assertEqual(status, 1)
            self.assertEqual(emitted[0]['type'], 'error')

    def test_helper_ends_on_stop_and_on_end_of_input(self):
        scan = {'type': 'scan', 'frequency': 0, 'time': 1.0, 'networks': []}
        status, emitted = self.run_helper(b'{"stop":true}\n', events=[scan])
        self.assertEqual(status, 0)
        status, emitted = self.run_helper(b'', events=[scan])
        self.assertEqual(status, 0)

    def test_helper_rejects_oversized_and_unknown_commands(self):
        scan = {'type': 'scan', 'frequency': 0, 'time': 1.0, 'networks': []}
        status, emitted = self.run_helper(b'x' * 5000, events=lambda *_: scan)
        self.assertEqual((status, emitted[-1]['message']), (1, 'Command too long'))
        status, emitted = self.run_helper(b'{"exec":"id"}\n', events=lambda *_: scan)
        self.assertEqual((status, emitted[0]['message']), (1, 'Command not allowed'))

    def test_permanent_failures_end_the_session_after_ten_errors(self):
        failure = {'type': 'error', 'message': 'Scan failed: not supported'}
        status, emitted = self.run_helper(events=[failure] * 20, after=lambda write: None)
        self.assertEqual(status, 1)
        self.assertEqual(sum(1 for event in emitted if event['message'].startswith('Scan failed')), scanner.MAX_ERRORS)
        self.assertEqual(emitted[-1]['message'], 'Too many consecutive scan errors. Scanning stopped.')

    def test_a_busy_adapter_never_counts_as_a_permanent_failure(self):
        busy = {'type': 'error', 'message': 'Adapter busy: waiting before retrying.'}
        scan = {'type': 'scan', 'frequency': 0, 'time': 1.0, 'networks': []}
        events = [busy] * 15 + [scan]
        status, emitted = self.run_helper(events=events, after=lambda write: threading.Timer(
            0.5, lambda: (os.write(write, b'{"stop":true}\n'), os.close(write))).start())
        self.assertEqual(status, 0)

    @patch('scanner.subprocess.run')
    def test_timeout_is_reported(self, run):
        run.side_effect = subprocess.TimeoutExpired('iw', 15)
        self.assertEqual(scan_once('wlan0', 0)['type'], 'error')


if __name__ == '__main__':
    unittest.main()
