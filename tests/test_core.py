import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from core import Network, SignalTracker, beep_interval, channel_for_frequency, parse_iw


SCAN = '''BSS aa:bb:cc:dd:ee:01(on wlan0)
	freq: 2412.0
	last seen: 100 ms ago
	signal: -71.50 dBm
	SSID: Office
	capability: ESS Privacy (0x0011)
	RSN:
BSS aa:bb:cc:dd:ee:02(on wlan0) -- associated
	freq: 5180
	signal: -44.00 dBm
	SSID: Office
BSS aa:bb:cc:dd:ee:03(on wlan0)
	freq: 2437
	last seen: 9500 ms ago
	signal: -35.00 dBm
	SSID:
BSS aa:bb:cc:dd:ee:04(on wlan0)
	freq: 2462
	SSID: Incomplete
'''


class CoreTests(unittest.TestCase):
    def test_distinguishes_same_ssid_and_preserves_sample_age(self):
        nets = parse_iw(SCAN)
        self.assertEqual(len(nets), 3)
        self.assertNotEqual(nets[0].key, nets[1].key)
        self.assertEqual(nets[0].signal, -71.5)
        self.assertEqual(nets[0].age, 0.1)
        self.assertEqual(nets[0].security, 'WPA2/3')
        self.assertEqual(nets[2].ssid, '')

    def test_ssid_escapes_are_decoded_and_unset_names_are_hidden(self):
        from core import decode_ssid
        self.assertEqual(decode_ssid(r'Caff\xc3\xa8'), 'Caffè')
        self.assertEqual(decode_ssid(r'a\\b'), 'a\\b')
        self.assertEqual(decode_ssid(r'\x00\x00\x00'), '')
        self.assertEqual(decode_ssid(r'bad\x1b[31m'), 'bad?[31m')
        self.assertEqual(decode_ssid(r'\xff\xfe'), '\ufffd\ufffd')
        self.assertEqual(len(decode_ssid('x' * 300)), 128)
        nets = parse_iw('BSS aa:bb:cc:dd:ee:09(on wlan0)\n\tfreq: 2412\n\tsignal: -50.00 dBm\n'
                        '\tSSID: Caff\\xc3\\xa8\n')
        self.assertEqual(nets[0].ssid, 'Caffè')

    def test_security_labels_follow_the_authentication_suites(self):
        def security(*lines):
            text = 'BSS aa:bb:cc:dd:ee:09(on wlan0)\n\tfreq: 5180\n\tsignal: -50.00 dBm\n' + '\n'.join(lines) + '\n'
            return parse_iw(text)[0].security
        self.assertEqual(security('\tRSN:', '\t\t * Authentication suites: PSK'), 'WPA2')
        self.assertEqual(security('\tRSN:', '\t\t * Authentication suites: SAE'), 'WPA3')
        self.assertEqual(security('\tRSN:', '\t\t * Authentication suites: PSK SAE'), 'WPA2/3')
        self.assertEqual(security('\tRSN:', '\t\t * Authentication suites: OWE'), 'OWE')
        self.assertEqual(security('\tWPA:', '\t\t * Authentication suites: PSK'), 'WPA')
        self.assertEqual(security('\tRSN:', '\t\t * Authentication suites: PSK', '\tWPA:',
                                  '\t\t * Authentication suites: PSK'), 'WPA2')

    def test_more_bands_and_dfs_channels(self):
        for freq, channel in [(4900, 180), (5260, 52), (5500, 100), (5720, 144), (5935, 2),
                              (2467, 12), (2472, 13), (2300, 0)]:
            self.assertEqual(channel_for_frequency(freq), channel, freq)

    def test_frequency_channels_include_special_cases(self):
        for freq, channel in [(2412, 1), (2484, 14), (5180, 36), (5935, 2), (5955, 1), (7115, 233)]:
            self.assertEqual(channel_for_frequency(freq), channel)
        self.assertEqual(channel_for_frequency(1000), 0)

    def test_only_target_and_fresh_samples_drive_feedback(self):
        nets = parse_iw(SCAN)
        tracker = SignalTracker(nets[0].key)
        tracker.observe([nets[1], nets[2]], 10)
        self.assertIsNone(tracker.value)
        tracker.observe(nets, 11)
        self.assertEqual(tracker.value, -71.5)
        self.assertAlmostEqual(tracker.last_seen, 10.9)
        self.assertFalse(tracker.fresh(15))
        self.assertIsNone(tracker.interval(15))

    def test_expiry_resets_smoothing_and_peak_is_resettable(self):
        net = Network('aa:bb:cc:dd:ee:01', 'Office', 2412, -80)
        tracker = SignalTracker(net.key)
        tracker.observe([net], 1)
        tracker.observe([Network(net.bssid, net.ssid, net.frequency, -40)], 2)
        self.assertGreater(tracker.value, -80)
        self.assertLess(tracker.value, -40)
        self.assertEqual(tracker.peak, -40)
        tracker.observe([Network(net.bssid, net.ssid, net.frequency, -90)], 10)
        self.assertEqual(tracker.value, -90)
        tracker.reset_peak()
        self.assertIsNone(tracker.peak)

    def test_cadence_is_monotonic_bounded_and_rejects_invalid_signal(self):
        intervals = [beep_interval(s) for s in range(-100, -19)]
        self.assertTrue(all(a >= b for a, b in zip(intervals, intervals[1:])))
        self.assertGreaterEqual(min(intervals), 160)
        self.assertLessEqual(max(intervals), 2200)
        for value in [None, math.nan, math.inf, 0, -200]:
            self.assertIsNone(beep_interval(value))
        self.assertLess(beep_interval(-55, -65, -40), beep_interval(-60, -65, -40))

    def test_repeated_cached_samples_do_not_extend_freshness(self):
        net = Network('aa:bb:cc:dd:ee:01', 'Office', 2412, -40, age=0)
        tracker = SignalTracker(net.key)
        tracker.observe([net], 10)
        cached = Network(net.bssid, net.ssid, net.frequency, -40, age=5)
        tracker.observe([cached], 15)
        self.assertFalse(tracker.fresh(15))
        self.assertEqual(len(tracker.history), 1)


if __name__ == '__main__':
    unittest.main()
