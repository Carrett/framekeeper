# Changelog

All notable changes to Framekeeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-07-21

### Fixed

- Prevent Plex from indexing recoverable movie and TV files in Framekeeper's
  trash directories.
- Add `.plexignore` protection to existing trash directories when Framekeeper
  starts without overwriting custom ignore rules.

### Added

- Add automated coverage for Plex trash exclusion behavior.

## [0.1.0] - 2026-07-21

### Added

- Browse and inspect movies and TV series stored on a NAS.
- Parse release names and extract technical metadata with `ffprobe`.
- Detect duplicate movies and episodes and recommend the best-quality copy.
- Move media to a recoverable trash directory, restore it, or permanently
  remove it after explicit confirmation.
- Mount-status checks and restricted CIFS remount support.
- Spanish-language web interface and project documentation.

[Unreleased]: https://github.com/Carrett/framekeeper/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Carrett/framekeeper/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Carrett/framekeeper/releases/tag/v0.1.0
