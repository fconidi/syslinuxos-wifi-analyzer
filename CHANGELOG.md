# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2026.11.2] - 2026-11-11

### Fixed
- Crash a few seconds after start: the timer that stops a stuck adapter lookup
  touched the lookup process after it had already finished and been deleted.

## [2026.11.1] - 2026-11-07

### Fixed
- Non-ASCII SSIDs are decoded as `iw` escapes them, and an all-zero SSID is
  treated as hidden, so names such as "Caffè" display and filter correctly.
- The helper's own error is shown instead of a generic authorization message; a
  cancelled authorization is told apart from a missing polkit agent, and Stop
  cancels a pending authorization dialog.
- Closing the window no longer freezes it while a scan finishes; the adapter
  list is read in the background and a missing `iw` is reported as such.
- The network table is updated in place, keeping the selected cell, scroll
  position and sort order; a radio that changes channel replaces its old row.
- Clashing keyboard shortcuts in English, Italian, French and German.
- The history graph scrolls with time and follows the chosen sensitivity, the
  gauge scales with the system font, and beeps are muted at volume zero.
- Titles and stale rows use the theme's colours.
- A scan is limited to the 500 strongest radios and to the amount of text read
  from `iw`; scanning stops after ten consecutive errors, all channels are
  scanned about once a second, and malformed deeply nested commands are ignored.
- Bytecode left by the privileged helper is removed when the package is removed.

### Added
- Scan-in-progress indicator, announced errors for assistive technology, and
  text descriptions and keyboard focus for the signal graphs.
- Precise labels for OWE, WPA3 and WPA2 networks, 6 GHz channels shown as such,
  and the 4.9 GHz band.

### Changed
- Singular status line for a single radio; the manual page names the English
  controls.

## [2026.10.3] - 2026-10-12

### Changed
- Corrected the application name to SysLinuxOS Wifi Analyzer.
- Renamed the command, installed paths, desktop entries and polkit action.
- The package replaces the previous one with the misspelled name on installation.

## [2026.10.2] - 2026-10-12

### Added
- Desktop message language detection, with English as the fallback.
- Interface, diagnostics and accessibility text in Italian, French, German and
  Spanish; localized desktop entries and polkit authentication prompts.

## [2026.10.1] - 2026-10-12

### Added
- Initial Wi-Fi discovery and access point locator.
- Signal gauge for a chosen BSSID, history, peak and audible feedback.
- Explicit demo mode; improved stale-signal and shutdown handling.

### Security
- Desktop audio stays unprivileged; only the restricted `iw` scan helper is
  authorized through polkit.
