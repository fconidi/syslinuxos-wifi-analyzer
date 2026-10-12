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
