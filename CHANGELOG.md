# Changelog

All notable changes to the Vidaa TV Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

(Library/protocol changes are tracked separately in the [`pyvidaa`](https://github.com/warrenrees/pyvidaa) repository.)

## [2.0.5]

### Fixed

- Pairing now uses the TV's real MAC address instead of a freshly generated random one.
  Dynamic-auth credentials are a hash derived from the client's MAC, and the TV recomputes
  that hash from its own hardware MAC to validate the connection — so a random MAC could
  never match. The TV accepted the initial connection and then silently dropped the session
  before the PIN reached the screen, which surfaced as "The TV did not respond" with nothing
  in the log to explain it. The MAC is now read from the SSDP descriptor when the TV was
  discovered, or from a UPnP probe on manual IP entry.
- A leftover authentication token for the host is cleared before a fresh pairing attempt.
  A token from an earlier interrupted attempt (or from before a TV factory reset) made the
  client try to reconnect with credentials the TV no longer honours instead of generating
  new ones, so the PIN prompt never appeared.
- A TV reporting both a wired and a wireless MAC now resolves to the same address whether it
  was found by discovery or by probing. Previously the two paths could pick different
  interfaces, so a TV paired via discovery would fail to re-authenticate later.
- The brand read from the SSDP descriptor is no longer overwritten while resolving the MAC.
  Brand is part of the authentication credentials, so on non-Hisense VIDAA sets (e.g. `tpv`)
  this produced credentials the TV rejected.
- Setting up a TV no longer fails with a generic "cannot connect" when the TV answers
  `getdeviceinfo` but not `gettvinfo`. The device ID also no longer falls back to the TV's IP
  address, which became the entry's unique ID and changed whenever DHCP reassigned the address.

### Changed

- The config flow probes the TV's UPnP descriptor once per setup instead of twice, which
  removes several seconds of delay when a TV is slow to answer or half asleep.

Thanks to @aidinmaxim for diagnosing and reporting the dynamic-auth MAC failure (#6).

## [2.0.4]

### Fixed

- Pairing holds a single connection open across showing the PIN and authenticating it. The TV
  binds the pairing session to that one connection, so authenticating on a fresh connection
  timed out.
- Device info is fetched on a token-authenticated reconnect after pairing succeeds, since the
  TV only serves `getdeviceinfo` on a token-authed session. This is what populates the model
  and firmware version on the newly created device.

## [2.0.3]

### Fixed

- The device now shows the TV's model, firmware version, IP, and MAC. The coordinator caches
  `getdeviceinfo` and the entities build their `DeviceInfo` from it; previously the info was
  fetched during the first refresh (before the device existed in the registry) and never
  applied, so model/firmware stayed blank.
- Pairing no longer re-prompts for a PIN when the TV is briefly slow to return device info
  after a successful authentication. `getdeviceinfo` is retried, and a miss is treated as
  non-fatal — the entry is created and device info is fetched after setup.
- The integration now sets up even when the TV is unreachable (e.g. in deep sleep). Previously
  setup failed with `ConfigEntryNotReady`, so the entities — including the power button that
  sends Wake-on-LAN — were never created and the TV couldn't be woken from Home Assistant.
  The coordinator reconnects on a later poll once the TV is on.
- Wake-on-LAN now also uses the TV's hardware MAC cached from `getdeviceinfo` (not just the
  config entry's `device_id`), so the power button can wake a TV that has been seen online this
  session even when the entry never stored a MAC. (If the entry has no MAC and the TV hasn't
  been reached since the last restart, set a `wol_mac` in the integration options.)

### Changed

- Pairing now distinguishes a rejected PIN ("Invalid PIN") from no response at all
  ("The TV did not respond to the PIN - it may have expired…"), so a timed-out PIN screen
  no longer just looks like a wrong PIN.
- Device info is re-fetched on reconnect, so a firmware update (which reboots the TV) is
  reflected in the device's firmware version without an integration reload.
- Diagnostics now include the coordinator's cached `device_data` (model, firmware, IP) so the
  device info the integration resolved is visible.

## [2.0.0]

Initial release of the Vidaa TV integration as a standalone repository, split out of the
`pyvidaa` project. The integration uses the `pyvidaa` library (from PyPI) for all TV
communication.

### Added

- Home Assistant integration for Hisense/Vidaa Smart TVs — domain `vidaa_tv`, display name
  "Vidaa TV": media player, remote, config flow (SSDP discovery + PIN pairing), diagnostics,
  and repair flows.
- VIDAA brand images (icon/logo) via the local `brand/` folder (HA 2026.3+).
- Remote: shows "Home" as the current activity when the TV is at the launcher.
