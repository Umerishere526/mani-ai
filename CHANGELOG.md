# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Mani's own safety flag now has to name a kind of concern: the eight kinds the safety screen already uses, or `other` for something it thought about that is not danger. A real kind pauses a running framework exactly as before, `other` is treated as no flag, and a missing or unrecognised kind still pauses (see spec 0004).
- The reply's `crisis` object accepts a flag with a kind and no reason, so a flag can no longer lose the turn by leaving the reason out.

### Fixed
- DBT STOP no longer stalls when the person describes an urge to act. The model's own flag used to pause the framework and drop the stage, so questions could be asked twice and some conversations never reached the body check in. On a 38 message test set, urge messages that paused the questions fell from 11 of 40 runs to 0 of 40, while risk messages still paused 148 of 150 runs, the same as before.

### Security
- The log line for a model safety flag no longer carries the model's summary of what the person said. It records the kind and the thread id only.
