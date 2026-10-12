# Origin and maintenance

SysLinuxOS Wifi Analyzer is a focused GPL-3+ WiFi discovery and source-location
application. Its BSS parsing is adapted from `WirelessEngine.parseIWoutput` in
[ghostop14/sparrow-wifi](https://github.com/ghostop14/sparrow-wifi),
`wirelessengine.py`, commit `ff21d8e443d30c87f9d85cd440dccb4e73712bff`.
Copyright 2017 ghostop14. Source inspected 2026-10-12.

This is not a renamed copy of the entire Sparrow suite. The UI, signal tracker,
audio, restricted scan helper and Debian packaging are new SysLinuxOS code,
Copyright 2026 Franco Conidi. The reduced parser preserves fractional dBm and
cache age, keys observations by BSSID/frequency, accepts hidden SSIDs and derives
the channel from frequency. Bluetooth, SDR, GPS, Falcon and DroneID are outside
this release. No Sparrow Python dependencies are needed.

## Design references

- iw scanning: https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html#scanning
- iw 6.9 local help: `scan [freq <freq>*] ... [lowpri,flush,...]`
- Qt audio: https://doc.qt.io/qt-5/qsoundeffect.html
- Qt process pipes: https://doc.qt.io/qt-5/qprocess.html

Qt audio is reused and loaded once; QTimer controls repetition. Scanning uses a
fixed executable with argument arrays, a cache flush and a bounded subprocess.
The UI uses QProcess pipes rather than a TCP service or a privileged Qt session.
