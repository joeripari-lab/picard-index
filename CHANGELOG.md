# The Picard Index — Engine Changelog

All notable changes to **The Picard Index (Temporal Parity & Reality Audit)** engine, scoring rules, sector taxonomy, and dashboard interface are documented in this file.

---

## [2.4.0] — 2026-11-23

### Added
- **ECDSA P-256 Canonical Provenance & Attestation (`sign_attestation.py`, `verify_index.py`)**:
  - Signs `attestation.json` on every official CI run using a private ECDSA P-256 key stored exclusively in GitHub Secrets (`PICARD_SIGNING_KEY`), publishing `picard_public.pem` and pinning its SHA-256 key fingerprint (`3f7655b2c4ca6b55...`).
  - Added live in-browser verification (`window.crypto.subtle`) and a **Canonical Provenance Modal** in the dashboard so any visitor can verify authenticity against altered clones.
- **Tier-1 Domain Allowlists & Grounding Verification**:
  - Enforced `allowedSourceDomains` across the 7 structural sectors and `allowedMemeDomains` for `MEME` (`+/-0.15%` per item, `+/-0.20%` net sector cap, exempt from Prong 1 / 2014 Test).
  - Unverified `sectorFeed` items are automatically zeroed (`[UNVERIFIED SOURCE ZEROED]`).
- **Prompt Integrity Lock (`promptTemplateSha256`)**:
  - Hashed `build_system_rules_prompt()` across both daily and weekly audit modes (`bb2c8b0d88ed79d0...`) in `engine_lock.json`.

### Changed
- **Deterministic Telemetry Engine (`update_parity.py`)**:
  - Added UTC date gate to prevent future-dated runs and locked Gemini `temperature: 0.0`.
  - Replaced LLM-reported `rawDelta`, `realignment`, `anomalies`, and `eventType` overrides with deterministic Python summation and structured `strictScrutiny` boolean enforcement.
  - Pruned future-dated telemetry entries (Days 7–9) back to Day 6 (`2026-11-23`, `75.9%`).
- **Anti-Tampering Engine Lock v2.4.0**:
  - Updated `engineSha256` to `688623179e9fc4c3206160d41a16ee20da539e9fa0ee9c8f55d94e83af894b1f` and logged the `2026-11-23` Objectivity Audit entry.

---

## [2.3.0] — 2026-11-20

### Added
- **Weekly Hindsight Audit Engine (7-Day Permanence Reconciliation)**:
  - Automates 7-day retrospective audits across trailing scored developments to enforce **Prong 3 (Irreversible Structural Permanence)**.
  - Automatically identifies whether past developments were stayed by emergency court injunctions, walked back by officials, or softened into standard speculative hype.
  - Generates an explicit **Reversion Adjustment Delta** strictly bounded to `+/-0.30%` per cycle.
- **Dedicated Weekly Hindsight UI Section**:
  - Full-width interactive card displaying active audit cycles, gross wire delta, net hindsight reversion, permanence retention rate, and comprehensive recorded reasoning.
  - **7-Day Prong 3 Audit Trail & Reversion Ledger**: Itemized list detailing each evaluated headline, its retrospective verdict (`AFFIRMED PERMANENT`, `PARTIAL REVERSION`, or `DISSOLVED`), delta adjustment, and explicit recorded justification.
  - Visual audit pills (`⚖`) in the day selector bar highlighting weekly audit milestones.
- **Cycle 1 Audit Record (Days 1–7)**:
  - Recorded first official Weekly Hindsight Audit for Day 7 (Cycle 1: Days 1–7), advancing baseline parity to 76.02% with a -0.10% reversion delta trimming premature speculative noise.

### Changed
- **Anti-Tampering Engine Integrity Lock v2.3.0**:
  - Updated `canonicalRules` in `engine_lock.json` with `weeklyHindsightAuditEnabled: true`, `weeklyHindsightLookbackDays: 7`, and `weeklyHindsightMaxReversionDelta: 0.3`.
  - Checksum sealed to `39a6a9137185d5b3dc16b32cf555086142db02960b9163b277eaef8398b99866`.
  - Documented third Objectivity Audit log entry in `engine_lock.json`.

---

## [2.2.0] — 2026-11-20

### Added
- **8th Reality Sector — `[LAW]` (Legal & Constitutional Guardrails)**:
  - Monitors judicial review, constitutional limits on executive power, international tribunals (*ICJ*, *ICC*), and statutory guardrails holding against administrative overreach.
  - Balanced 8-category wire feed: `POL`, `ECON`, `TECH`, `SOC`, `GLOB`, `SCI`, `LAW`, and `MEME`.
  - Required daily minimum items increased to **16 items/day** (`minItemsPerSector >= 2`).
- **Interactive About Modal**:
  - Direct UI documentation detailing the origin of the index, the 75.0% PFA sovereign anchor, the 4-Prong Strict Scrutiny Gatekeeper, tier-1 citation standards, and cryptographic engine locking.
- **Interactive In-App Changelog**:
  - Modal added to the dashboard header to allow public auditing of engine changes directly from the interface.

### Changed
- **Full-Width Layout Rebalancing**:
  - Expanded the **4-Prong Strict Scrutiny Audit** and **Temporal Forecast** to span the full width of the page (`col-span-12`), eliminating horizontal compression and enhancing readability.
  - Rebalanced the Engine Codex and 9-Trope Echo Watchlist side-by-side (`col-span-6` each).
- **Anti-Tampering Engine Lock v2.2.0**:
  - Recalculated and locked `canonicalRules` SHA-256 hash to `7858df1cb28d0036454304a66952ceb29c7553c6b5ef726090fd920966cee309`.
  - Appended Objectivity Audit entry to `engine_lock.json`.

### Removed
- Removed the obsolete reset button from the top navigation bar.
- Removed obsolete `IMPORT JSON` and `EXPORT` functions, drop zone, and simulation handlers from the dashboard to enforce pure read-only public telemetry verification.

---

## [2.1.0] — 2026-11-20

### Added
- **7th Reality Sector — `[MEME]` (Pop & Internet Culture)**:
  - Tracks viral internet phenomena, box-office/entertainment inflection points, and cultural realignments.
  - Enforced bounded sub-cap of `+/- 0.15%` max delta per item.
  - Explicit rule: `MEME` sector events cannot trigger an uncapped `TCE` or `TFE`.
- **Anti-Tampering Engine Integrity Lock (`engine_lock.json`)**:
  - Mathematical SHA-256 seal protecting core rules (`standardDailyCap`, `pfaBaseline`, `memeSectorMaxItemDelta`, multipliers, required sectors, prongs).
  - Pre-flight automated CI check in `.github/workflows/daily-parity.yml` that halts pipeline execution on unauthorized rule drift.
  - Documented Objectivity Audit log protocol.

---

## [2.0.0] — 2026-11-20

### Added
- **100% Serverless Architecture**:
  - Replaced external VM infrastructure with GitHub Actions automated cron (`15:10 UTC` / 10:10 AM EST) and GitHub Pages deployment.
  - Zero-dependency ingestion engine (`update_parity.py`) using Python standard library.
  - Google Gemini API integration with automated Google Search grounding for real-time news retrieval.
- **Next-Gen Cyberpunk / Sci-Fi Command Terminal Dashboard**:
  - Pure CSS design system with deep midnight background (`#060810`), LCARS glowing accents (`#ffaa00`, `#00e5ff`, `#ff2e63`, `#00ff9d`).
  - Interactive SVG Trajectory Chart with area curves, hover tooltips, and Full Arc vs Post-PFA toggle.
  - Quick-navigation Day Selector Pills across all historic epochs.
  - Dynamic HTML5 Canvas Dispatch Share Card generator (1200x675 PNG).
  - JSON Import / Export modal with drag-and-drop.

---

## [1.0.0] — 2026-10-28 to 2026-11-16

### Added
- **Foundational Codex & Sovereignty Anchor**:
  - Defined **Epoch 0 (2016-05-28)**: The Harambe Incident at Cincinnati Zoo severing Prime timeline continuity (`100.0% -> 0.0%`).
  - Established **Picard's Final Act (PFA — 2026-10-28)**: Dynamic sovereign baseline reset (`+67.5%` applied) bridging the 7.5% trough to anchor reality at **75.0% (The Picard Standard)**.
  - Opened and consolidated the 14-day Correction Window through November 16, 2026.
- **The 4-Prong Strict Scrutiny Gatekeeper**:
  - Prong 1: The 2014 Test (Baseline Survival Filter).
  - Prong 2: Causal Independence (No Double-Counting).
  - Prong 3: Irreversible Structural Permanence.
  - Prong 4: Multi-Outlet Empirical Verification.
- **Scoring Rules & 6 Original Sectors**:
  - Standard daily cap: `+/- 0.5%`.
  - 1.5x Cascading Nonsense Policy Multiplier.
  - 6 initial sectors: `POL`, `ECON`, `TECH`, `SOC`, `GLOB`, `SCI`.
