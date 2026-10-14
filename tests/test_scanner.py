import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
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
    def test_timeout_is_reported(self, run):
        run.side_effect = subprocess.TimeoutExpired('iw', 15)
        self.assertEqual(scan_once('wlan0', 0)['type'], 'error')


if __name__ == '__main__':
    unittest.main()
