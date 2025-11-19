## 3.0.0 - 2025-10-03

### ✨ New Features

- Deliver zero gaps guarantee by default with auto-fill Implement automatic gap detection and filling in download() and fetch*data() to fulfill the package's core promise of "zero gaps guarantee". Previous Behavior (BROKEN): - Package name: gapless-crypto-data - Promise: "zero gaps guarantee" in README - Reality: download() returned data with gaps from Binance Vision - User complaint: False advertising - had to manually discover and call fill_gaps() New Behavior (FIXED): - auto_fill_gaps=True by default in download() and fetch_data() - Automatically detects gaps using UniversalGapFiller - Fills gaps with authentic Binance API data - Logs gap-filling activity for transparency - Opt-out available: auto_fill_gaps=False for raw Vision data Implementation Details: - Added auto_fill_gaps parameter to both download() and fetch_data() - Integrated UniversalGapFiller.process_file() into data collection flow - Automatic DataFrame reload after gap filling - Clear logging: "✅ Auto-filled N/M gap(s)" or warning if fill fails - Enhanced docstrings with "zero gaps guarantee" language Testing: - Added 4 comprehensive test cases in test_simple_api.py: * test*auto_fill_gaps_enabled_by_default() * test*auto_fill_gaps_can_be_disabled() * test*fetch_data_auto_fill_parameter() * test_download_delivers_zero_gaps_guarantee() - March 24, 2023 gap scenario validation Addresses user complaint: /tmp/github_issue_gapless_crypto_data.md - Gap-filling capability existed but wasn't integrated by default - Users discovered gaps in production after trusting package name - Had to manually diagnose, call fill_gaps(), and reload data BREAKING CHANGE: download() and fetch_data() now automatically fill gaps by default, which may result in additional API calls for data with gaps. Users can disable with auto_fill_gaps=False to maintain previous behavior. (by @terrylica)

### 🐛 Bug Fixes & Improvements

- Add contents:write permission for Sigstore artifact signing Allows Sigstore action to attach signed artifacts to GitHub releases (by @terrylica)

---

**Full Changelog**: https://github.com/terrylica/rangebar/compare/v2.16.0...v3.0.0
