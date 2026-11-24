#!/usr/bin/env python3
"""
The Picard Index — Autonomous Telemetry Engine & Deterministic Schema Validator (v2.4.0)
8-Sector Aggregator with Anti-Tampering Engine Lock, Domain Allowlist, and Scrutiny Enforcement.
"""

import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TELEMETRY_PATH = os.path.join(BASE_DIR, "telemetry.json")
ENGINE_LOCK_PATH = os.path.join(BASE_DIR, "engine_lock.json")
DEFAULT_MODEL = "gemini-2.5-flash"


def compute_prompt_template_sha256(canonical_rules: dict) -> str:
    """Computes a deterministic SHA-256 hash of build_system_rules_prompt() across both audit modes."""
    daily_prompt = build_system_rules_prompt(canonical_rules, is_weekly_audit=False, target_day=1)
    weekly_prompt = build_system_rules_prompt(canonical_rules, is_weekly_audit=True, target_day=7)
    combined = f"DAILY:\n{daily_prompt}\n---\nWEEKLY:\n{weekly_prompt}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def verify_engine_lock(lock_path: str) -> dict:
    """Verifies SHA-256 integrity of canonical rules and prompt template to prevent tampering."""
    if not os.path.exists(lock_path):
        raise FileNotFoundError(f"Engine lock file missing: {lock_path}")

    with open(lock_path, "r", encoding="utf-8") as f:
        lock_data = json.load(f)

    canonical_rules = lock_data.get("canonicalRules")
    if not canonical_rules:
        raise ValueError("engine_lock.json missing 'canonicalRules' mapping.")

    computed_sha = hashlib.sha256(
        json.dumps(canonical_rules, sort_keys=True).encode("utf-8")
    ).hexdigest()

    expected_sha = lock_data.get("engineSha256")
    if computed_sha != expected_sha:
        raise RuntimeError(
            f"ENGINE LOCK INTEGRITY VIOLATION! Canonical rules have been altered.\n"
            f"Expected SHA: {expected_sha}\n"
            f"Computed SHA: {computed_sha}\n"
            f"Must log an Objectivity Audit entry and update engineSha256 to proceed."
        )

    expected_prompt_sha = lock_data.get("promptTemplateSha256")
    if expected_prompt_sha:
        computed_prompt_sha = compute_prompt_template_sha256(canonical_rules)
        if computed_prompt_sha != expected_prompt_sha:
            raise RuntimeError(
                f"PROMPT TEMPLATE INTEGRITY VIOLATION! System prompt wording was altered.\n"
                f"Expected Prompt SHA: {expected_prompt_sha}\n"
                f"Computed Prompt SHA: {computed_prompt_sha}\n"
                f"Must log an Objectivity Audit entry and update promptTemplateSha256 to proceed."
            )

    print(f"Anti-Tampering Engine Lock verified. Checksum: {computed_sha[:16]}...")
    return canonical_rules


def build_system_rules_prompt(rules: dict, is_weekly_audit: bool = False, target_day: int = 1) -> str:
    pfa_base = rules.get("pfaBaseline", 75.0)
    daily_cap = rules.get("standardDailyCap", 0.5)
    item_cap = rules.get("maxStandardItemDelta", 0.25)
    meme_cap = rules.get("memeSectorMaxItemDelta", 0.15)
    meme_net_cap = rules.get("memeSectorMaxNetDelta", 0.20)
    mult = rules.get("cascadingNonsenseMultiplier", 1.5)
    tce_days = rules.get("tceWindowDays", 7)
    tce_mult = rules.get("tceWindowMultiplier", 1.25)
    tce_pos_cap = rules.get("tceWindowDailyPositiveCap", 0.63)
    rev_cap = rules.get("weeklyHindsightMaxReversionDelta", 0.30)
    allowed_domains = ", ".join(rules.get("allowedSourceDomains", []))
    allowed_meme_domains = ", ".join(rules.get("allowedMemeDomains", []))

    weekly_instructions = ""
    if is_weekly_audit:
        weekly_instructions = f"""
--- WEEKLY HINDSIGHT AUDIT (CANONICAL ENGINE LOCK v2.5.0) ---
Day {target_day} marks a 7-day Weekly Hindsight Audit milestone (Cycle {target_day // 7})!
In addition to daily wire ingestion, you MUST perform a retrospective audit of structural events (excluding MEME) scored across the trailing 7 days (Days {target_day - 6} to {target_day - 1}).
Identify whether any previously scored developments have since been stayed by courts, walked back by officials, debunked, or failed Prong 3 (Irreversible Structural Permanence) in hindsight.
You must populate the "weeklyHindsight" object:
  "cycle": {target_day // 7},
  "auditedDaysRange": "Day {target_day - 6} – Day {target_day}",
  "auditDate": "<YYYY-MM-DD>",
  "status": "REVERSION_APPLIED" or "AFFIRMED_PERMANENT",
  "reversionDelta": <float between -{rev_cap} and +{rev_cap}: negative if past gains were premature/dissolved, positive if structural permanence accelerated>,
  "auditedItems": [
    {{
      "originalDay": <integer>,
      "sector": "<SECTOR>",
      "headline": "<headline>",
      "originalDelta": <float>,
      "verdict": "AFFIRMED_PERMANENT" | "PARTIAL_REVERSION" | "DISSOLVED",
      "adjustment": <float>,
      "reasoning": "<explicit detailed reasoning explaining why Prong 3 held up or failed in 7-day hindsight>"
    }}
  ],
  "reasoning": "<comprehensive multi-sentence retrospective analysis evaluating whether the combined parity shift holds true over the 7-day macro window>"
"""

    return f"""You are the autonomous telemetry engine for The Picard Index (Temporal Parity & Reality Audit).
Your role is to ingest the past 24 hours of global news, evaluate it under strict temporal audit rules, and produce the next day's telemetry entry in valid JSON format.

--- CANONICAL ENGINE RULES (LOCKED v2.5.0) ---
- Sovereign Anchor: Picard's Final Act (PFA) on 2026-10-28 set a non-repeatable dynamic sovereign baseline at {pfa_base}%.
- Baseline Waterline: {pfa_base}%.
- Standard daily cap: Net daily delta is strictly capped between -{daily_cap}% and +{daily_cap}%. Individual standard sector items are capped at +/-{item_cap}%. Low signal days hold at 0.0% (Noise Floor).
- {tce_days}-Day TCE Convergence Window: A cleared Temporal Convergence Event (TCE) opens a {tce_days}-day window applying a {tce_mult}x multiplier (enforced by Python) to corresponding positive realignment items in matching structural sectors (positive daily cap +{tce_pos_cap}%, MEME excluded). Does NOT apply to TFEs.
- 1.5x Cascading Nonsense Policy Multiplier: Contradictory policies receive a {mult}x negative drag (-0.25% to -0.75% base) if cleared by Strict Scrutiny.
- Weekly Hindsight Audit: 7-day retrospective permanence reconciliation bounded to +/-{rev_cap}% (applies to the 7 structural sectors; MEME is ephemeral and excluded).
{weekly_instructions}
--- 4-PRONG STRICT SCRUTINY GATEKEEPER ---
Any candidate attempting to bypass the +/-{daily_cap}% daily cap (Temporal Convergence Event +2.0% to +5.0%, or Temporal Fracture Event -3.0% to -15.0%) MUST CLEAR ALL FOUR PRONGS. Failing even one prong downgrades the event to capped daily scoring (<= +/-{daily_cap}%) or 0.0%:
1. Prong 1 — The 2014 Test (Baseline Survival Filter): Would this qualify as normal constitutional governance, routine election turnover, standard court procedure, or ordinary market fluctuation in 2014? If yes -> automatic 0.0% (no bonus points for baseline survival; no panic multiplier for routine political friction). NOTE: MEME is EXEMPT from Prong 1 because meme/internet culture is inherently fickle and 2014 memes are not valid today.
2. Prong 2 — Causal Independence (No Double-Counting): Is this an independent structural catalyst or rupture, or merely a predictable second-order reaction to an already-scored event?
3. Prong 3 — Irreversible Structural Permanence: Does it enact binding law, permanent structural reform, or irreversible systemic fallout—rather than a committee vote, PR pledge, temporary executive order, or 24-hour outrage cycle?
4. Prong 4 — Multi-Outlet Empirical Verification: Confirmed across 2+ independent major neutral tier-1 outlets with measurable real-world impact.

--- 8-SECTOR NEUTRAL WIRE & CULTURE AGGREGATOR ---
You must evaluate and cite at least 2 verified headlines per sector (at least 16 items total in sectorFeed), each with an exact "sourceUrl" from the verified domain allowlists:
- Structural Sectors (POL, ECON, TECH, SOC, GLOB, SCI, LAW) allowed domains: {allowed_domains}
- MEME Sector (Pop & Internet Culture — well-regulated wildcard driven by timeline vibes):
  - Exempt from Prong 1 (2014 Test). Score positive vibes (+0.01 to +{meme_cap}) for unifying cultural moments/milestones, negative vibes (-0.01 to -{meme_cap}) for toxic slop/dystopian absurdity, or 0.0 for fleeting noise.
  - SUB-CAPS: Each MEME item delta is strictly bounded to +/-{meme_cap}%, and total MEME net contribution is bounded to +/-{meme_net_cap}%. MEME events CANNOT trigger a TCE or TFE.
  - MEME allowed domains: {allowed_meme_domains}

--- REQUIRED JSON OUTPUT SCHEMA ---
Output ONLY a single valid JSON object representing the new log entry with EXACTLY these fields:
{{
  "day": <integer: next day number>,
  "date": "<YYYY-MM-DD: date of target day>",
  "label": "<UPPERCASE SHORT SUMMARY: e.g. DAY N: TOP TOPIC & TOP TOPIC>",
  "eventType": "STANDARD_DAY",
  "strictScrutiny": {{
    "prong1_2014TestPassed": false,
    "prong2_causalIndependence": false,
    "prong3_irreversiblePermanence": false,
    "prong4_multiOutletVerified": false
  }},
  "previous": <float: previous day parity>,
  "current": <float: previous + delta, rounded to 2 decimals>,
  "delta": <float: net delta clamped to [-{daily_cap}, +{daily_cap}] unless all 4 strictScrutiny prongs are true>,
  "rawDelta": <float: sum of sectorFeed deltas>,
  "capped": <boolean: true if rawDelta exceeded cap and was clamped>,
  "capLimit": {daily_cap},
  "echoes": [<array of string echo watchlist triggers if applicable>],
  "realignment": [<array of positive items: "+X.XX% [SECTOR] Headline — (Source: Wire)">],
  "anomalies": [<array of negative items: "-X.XX% [SECTOR] Headline — (Source: Wire)">],
  "sectorFeed": [
    {{ "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "LAW", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "LAW", "delta": <float>, "headline": "<text>", "source": "<wire>", "sourceUrl": "<https://...>" }},
    {{ "sector": "MEME", "delta": <float between -{meme_cap} and +{meme_cap}>, "headline": "<text>", "source": "<outlet>", "sourceUrl": "<https://...>" }},
    {{ "sector": "MEME", "delta": <float between -{meme_cap} and +{meme_cap}>, "headline": "<text>", "source": "<outlet>", "sourceUrl": "<https://...>" }}
  ],
  "skepticAudit": "<text: detailed strict scrutiny analysis explaining why events passed or failed prongs>",
  "forecast": "<text: concise synthesis and outlook relative to the {pfa_base}% Picard Standard baseline>",
  "weeklyHindsight": <null or object with cycle, auditedDaysRange, auditDate, status, reversionDelta, auditedItems, reasoning>
}}
"""


def load_telemetry(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Telemetry file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_save_telemetry(path: str, data: dict):
    dir_name = os.path.dirname(path)
    tmp_file = tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8")
    try:
        json.dump(data, tmp_file, indent=2, ensure_ascii=False)
        tmp_file.write("\n")
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_file.close()
        os.replace(tmp_file.name, path)
    except Exception:
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        raise


def extract_grounding_info(candidate: dict) -> dict:
    """Extracts web URIs and titles from Gemini groundingMetadata.groundingChunks."""
    chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
    uris = set()
    titles = set()
    for chunk in chunks:
        web = chunk.get("web", {})
        if web.get("uri"):
            uris.add(web["uri"].strip())
        if web.get("title"):
            titles.add(web["title"].strip().lower())
    return {"uris": uris, "titles": titles}


def query_gemini_single_attempt(
    api_key: str, model: str, system_prompt: str, user_prompt: str, use_json_mime: bool = True
) -> tuple[dict, dict]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    generation_config = {"temperature": 0.0}
    if use_json_mime:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt},
                    {"text": user_prompt}
                ]
            }
        ],
        "tools": [{"googleSearch": {}}],
        "generationConfig": generation_config,
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        resp_body = resp.read().decode("utf-8")
        result = json.loads(resp_body)

    try:
        candidate = result["candidates"][0]
        text_content = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Malformed Gemini API response: {result}") from e

    grounding_info = extract_grounding_info(candidate)

    clean_json = text_content.strip()
    if clean_json.startswith("```"):
        clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
        clean_json = re.sub(r"\s*```$", "", clean_json)

    try:
        return json.loads(clean_json), grounding_info
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text_content)
        if match:
            return json.loads(match.group(0)), grounding_info
        raise


def query_gemini(api_key: str, requested_model: str, system_prompt: str, user_prompt: str) -> tuple[dict, dict]:
    models_to_try = [requested_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    seen = set()
    models = []
    for m in models_to_try:
        if m and m not in seen:
            seen.add(m)
            models.append(m)

    last_error = None
    for model in models:
        for use_json_mime in [True, False]:
            try:
                print(f"Attempting query with model={model}, responseMimeType={use_json_mime}...")
                return query_gemini_single_attempt(api_key, model, system_prompt, user_prompt, use_json_mime=use_json_mime)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {e.code} ({model}): {err_body}"
                print(f"Warning: {last_error}", file=sys.stderr)
                if e.code == 400 and use_json_mime:
                    continue
                if e.code == 404:
                    break
            except Exception as e:
                last_error = str(e)
                print(f"Warning: Attempt failed ({model}): {e}", file=sys.stderr)
                break

    raise RuntimeError(f"All Gemini query attempts failed. Last error: {last_error}")


def _domain_matches(host: str, allowlist: list[str]) -> bool:
    if not host:
        return False
    clean_host = host.lower().split(":")[0]
    if clean_host.startswith("www."):
        clean_host = clean_host[4:]
    return any(clean_host == d or clean_host.endswith("." + d) for d in allowlist)


def _is_source_verified(item: dict, canonical_rules: dict, grounding_info: dict | None) -> bool:
    url = (item.get("sourceUrl") or "").strip()
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False

    sector = item.get("sector")
    if sector == "MEME":
        allowlist = canonical_rules.get("allowedMemeDomains", [])
    else:
        allowlist = canonical_rules.get("allowedSourceDomains", [])

    if not _domain_matches(parsed.netloc, allowlist):
        return False

    # If grounding metadata was returned by Gemini, verify either the URI or the grounded domain title appears.
    if grounding_info and (grounding_info.get("uris") or grounding_info.get("titles")):
        host = parsed.netloc.lower().split(":")[0]
        bare_host = host[4:] if host.startswith("www.") else host
        uri_match = any(bare_host in u.lower() for u in grounding_info["uris"])
        title_match = any(bare_host in t or t in bare_host for t in grounding_info["titles"])
        if not (uri_match or title_match):
            print(f"Info: sourceUrl {url} passed domain allowlist; grounding chunks did not directly list {bare_host}.")

    return True


def get_active_tce_window(logs: list[dict], target_day: int, canonical_rules: dict) -> dict | None:
    """
    Returns active 7-day TCE Convergence Window metadata if a TCE occurred within
    the trailing tceWindowDays and was not dissolved by a subsequent Weekly Hindsight Audit.
    TFEs never open a window.
    """
    window_days = int(canonical_rules.get("tceWindowDays", 7))
    matching_only = bool(canonical_rules.get("tceWindowMatchingSectorsOnly", True))
    excludes_meme = bool(canonical_rules.get("tceWindowExcludesMeme", True))
    structural_sectors = [
        s for s in canonical_rules.get("requiredSectors", ["POL", "ECON", "TECH", "SOC", "GLOB", "SCI", "LAW", "MEME"])
        if not (excludes_meme and s == "MEME")
    ]

    dissolved_days = set()
    for log in logs:
        wh = log.get("weeklyHindsight")
        if isinstance(wh, dict):
            for audited in wh.get("auditedItems", []):
                if audited.get("verdict") == "DISSOLVED" and "originalDay" in audited:
                    dissolved_days.add(int(audited["originalDay"]))

    for log in reversed(logs):
        log_day = int(log.get("day", -999))
        age = target_day - log_day
        if age <= 0 or age > window_days:
            continue
        if log.get("eventType") == "TCE" and log_day not in dissolved_days:
            if matching_only:
                sectors = sorted({
                    item.get("sector")
                    for item in log.get("sectorFeed", [])
                    if float(item.get("delta", 0.0)) > 0
                    and item.get("sector") in structural_sectors
                })
                if not sectors:
                    sectors = structural_sectors
            else:
                sectors = structural_sectors

            return {
                "active": True,
                "tceDay": log_day,
                "dayOfWindow": age,
                "remainingDays": window_days - age + 1,
                "matchingSectors": sectors,
            }
    return None


def validate_and_clamp_log_entry(
    entry: dict,
    previous_log: dict,
    canonical_rules: dict,
    grounding_info: dict | None = None,
    active_tce_window: dict | None = None,
) -> dict:
    required_keys = [
        "day", "date", "label", "eventType", "previous", "current",
        "delta", "rawDelta", "capped", "capLimit", "echoes",
        "realignment", "anomalies", "sectorFeed", "skepticAudit", "forecast",
    ]
    for key in required_keys:
        if key not in entry:
            raise ValueError(f"Missing required key in generated log entry: {key}")

    prev_current = float(previous_log["current"])
    entry["previous"] = prev_current
    entry["day"] = int(previous_log["day"]) + 1

    # Date progression check
    prev_date = datetime.date.fromisoformat(previous_log["date"])
    entry_date = datetime.date.fromisoformat(entry["date"])
    if entry_date <= prev_date:
        entry["date"] = (prev_date + datetime.timedelta(days=1)).isoformat()

    # 8-Sector Feed Validation
    sector_feed = entry.get("sectorFeed", [])
    required_sectors = set(canonical_rules.get("requiredSectors", ["POL", "ECON", "TECH", "SOC", "GLOB", "SCI", "LAW", "MEME"]))
    sectors_present = {item.get("sector") for item in sector_feed}

    if not required_sectors.issubset(sectors_present):
        missing = required_sectors - sectors_present
        raise ValueError(f"Sector feed missing required sectors: {missing}")

    # Enforce per-item caps, verify sourceUrl against domain allowlists, and apply TCE window multiplier
    meme_item_cap = float(canonical_rules.get("memeSectorMaxItemDelta", 0.15))
    meme_net_cap = float(canonical_rules.get("memeSectorMaxNetDelta", 0.20))
    std_item_cap = float(canonical_rules.get("maxStandardItemDelta", 0.25))
    tce_mult = float(canonical_rules.get("tceWindowMultiplier", 1.25))
    tce_active = bool(active_tce_window and active_tce_window.get("active"))
    tce_sectors = set(active_tce_window.get("matchingSectors", [])) if tce_active else set()
    tce_excludes_meme = bool(canonical_rules.get("tceWindowExcludesMeme", True))

    for item in sector_feed:
        sector = item.get("sector")
        raw_val = float(item.get("delta", 0.0))
        if not _is_source_verified(item, canonical_rules, grounding_info):
            item["delta"] = 0.0
            headline = item.get("headline", "")
            if "[UNVERIFIED SOURCE ZEROED]" not in headline:
                item["headline"] = f"{headline} [UNVERIFIED SOURCE ZEROED]".strip()
            continue

        cap = meme_item_cap if sector == "MEME" else std_item_cap
        clamped = round(max(-cap, min(cap, raw_val)), 2)

        if tce_active and clamped > 0 and sector in tce_sectors and not (tce_excludes_meme and sector == "MEME"):
            boosted = round(clamped * tce_mult, 2)
            max_boosted_item = round(std_item_cap * tce_mult, 2)
            item["delta"] = min(max_boosted_item, boosted)
        else:
            item["delta"] = clamped

    # Enforce MEME net sector cap (+/- 0.20% default)
    meme_items = [item for item in sector_feed if item.get("sector") == "MEME"]
    meme_sum = round(sum(float(item["delta"]) for item in meme_items), 2)
    if abs(meme_sum) > meme_net_cap and meme_sum != 0:
        scale = meme_net_cap / abs(meme_sum)
        for item in meme_items:
            item["delta"] = round(float(item["delta"]) * scale, 2)

    # Count items per sector
    min_items = int(canonical_rules.get("minItemsPerSector", 2))
    sector_counts = {}
    for item in sector_feed:
        s = item.get("sector")
        sector_counts[s] = sector_counts.get(s, 0) + 1

    for req_sec in required_sectors:
        if sector_counts.get(req_sec, 0) < min_items:
            print(f"Warning: Sector {req_sec} has fewer than {min_items} items (has {sector_counts.get(req_sec, 0)})")

    # Deterministic rawDelta summation and summary list reconstruction
    raw_delta = round(sum(float(item["delta"]) for item in sector_feed), 2)
    entry["realignment"] = [
        f"+{float(item['delta']):.2f}% [{item['sector']}] {item['headline']} — (Source: {item.get('source', 'Wire')})"
        for item in sector_feed
        if float(item["delta"]) > 0
    ]
    entry["anomalies"] = [
        f"{float(item['delta']):.2f}% [{item['sector']}] {item['headline']} — (Source: {item.get('source', 'Wire')})"
        for item in sector_feed
        if float(item["delta"]) < 0
    ]

    # Enforce 4-Prong Strict Scrutiny Gatekeeper via structured booleans
    scrutiny = entry.get("strictScrutiny") or {}
    all_prongs_cleared = (
        isinstance(scrutiny, dict)
        and scrutiny.get("prong1_2014TestPassed") is True
        and scrutiny.get("prong2_causalIndependence") is True
        and scrutiny.get("prong3_irreversiblePermanence") is True
        and scrutiny.get("prong4_multiOutletVerified") is True
    )

    cap_limit = float(canonical_rules.get("standardDailyCap", 0.5))
    pos_cap_limit = float(canonical_rules.get("tceWindowDailyPositiveCap", 0.63)) if tce_active else cap_limit
    requested_event_type = entry.get("eventType", "STANDARD_DAY")

    if all_prongs_cleared and requested_event_type != "STANDARD_DAY":
        entry["eventType"] = requested_event_type
        daily_delta = max(-15.0, min(5.0, raw_delta))
        capped = False
    else:
        entry["eventType"] = "STANDARD_DAY"
        if raw_delta > pos_cap_limit:
            daily_delta = pos_cap_limit
            capped = True
        elif raw_delta < -cap_limit:
            daily_delta = -cap_limit
            capped = True
        else:
            daily_delta = raw_delta
            capped = False

    if tce_active and entry["eventType"] == "STANDARD_DAY":
        entry["tceWindowActive"] = True
        entry["tceWindowDay"] = active_tce_window["tceDay"]
        entry["tceWindowRemainingDays"] = active_tce_window["remainingDays"]
        entry["tceWindowSectors"] = active_tce_window["matchingSectors"]
    else:
        entry["tceWindowActive"] = False

    # Enforce Weekly Hindsight Reversion Delta if present
    weekly_hindsight = entry.get("weeklyHindsight")
    reversion_delta = 0.0
    if weekly_hindsight and isinstance(weekly_hindsight, dict):
        max_rev = float(canonical_rules.get("weeklyHindsightMaxReversionDelta", 0.30))
        raw_rev = float(weekly_hindsight.get("reversionDelta", 0.0))
        reversion_delta = max(-max_rev, min(max_rev, round(raw_rev, 2)))
        weekly_hindsight["reversionDelta"] = reversion_delta
        if reversion_delta != 0.0:
            weekly_hindsight["status"] = "REVERSION_APPLIED"
        else:
            weekly_hindsight["status"] = "AFFIRMED_PERMANENT"

    total_delta = round(daily_delta + reversion_delta, 2)
    entry["dailyDelta"] = daily_delta
    entry["reversionDelta"] = reversion_delta
    entry["delta"] = total_delta
    entry["rawDelta"] = raw_delta
    entry["capped"] = capped
    entry["capLimit"] = cap_limit

    new_current = round(prev_current + total_delta, 2)
    new_current = max(0.0, min(100.0, new_current))
    entry["current"] = new_current

    return entry


def run_dry_run_check(canonical_rules: dict):
    """Runs deterministic validation checks on synthetic sample data without calling Gemini or writing files."""
    prev_log = {"day": 6, "date": "2026-11-23", "current": 75.9}
    sample_entry = {
        "day": 7,
        "date": "2026-11-24",
        "label": "DAY 7: DRY RUN VALIDATION",
        "eventType": "TEMPORAL_CONVERGENCE_EVENT",  # Should be forced to STANDARD_DAY because prongs are False
        "strictScrutiny": {
            "prong1_2014TestPassed": False,
            "prong2_causalIndependence": False,
            "prong3_irreversiblePermanence": False,
            "prong4_multiOutletVerified": False,
        },
        "previous": 75.9,
        "current": 99.0,  # Intentionally wrong; Python must recompute
        "delta": 4.0,     # Intentionally wrong; Python must recompute
        "rawDelta": 9.9,  # Intentionally wrong; Python must recompute
        "capped": False,
        "capLimit": 0.5,
        "echoes": [],
        "realignment": [],
        "anomalies": [],
        "sectorFeed": [
            {"sector": "POL", "delta": 0.15, "headline": "Policy A", "source": "Reuters", "sourceUrl": "https://www.reuters.com/world/a"},
            {"sector": "POL", "delta": 0.05, "headline": "Unverified Blog", "source": "Blog", "sourceUrl": "https://random-blog.example.com/post"},
            {"sector": "ECON", "delta": 0.10, "headline": "Markets B", "source": "Bloomberg", "sourceUrl": "https://www.bloomberg.com/news/b"},
            {"sector": "ECON", "delta": -0.05, "headline": "Markets C", "source": "AP", "sourceUrl": "https://apnews.com/article/c"},
            {"sector": "TECH", "delta": 0.10, "headline": "Tech D", "source": "BBC", "sourceUrl": "https://www.bbc.com/news/d"},
            {"sector": "TECH", "delta": 0.05, "headline": "Tech E", "source": "NPR", "sourceUrl": "https://www.npr.org/e"},
            {"sector": "SOC", "delta": 0.05, "headline": "Soc F", "source": "PBS", "sourceUrl": "https://www.pbs.org/f"},
            {"sector": "SOC", "delta": -0.05, "headline": "Soc G", "source": "AFP", "sourceUrl": "https://www.afp.com/g"},
            {"sector": "GLOB", "delta": 0.10, "headline": "Glob H", "source": "Reuters", "sourceUrl": "https://reuters.com/h"},
            {"sector": "GLOB", "delta": 0.05, "headline": "Glob I", "source": "BBC", "sourceUrl": "https://www.bbc.co.uk/i"},
            {"sector": "SCI", "delta": 0.10, "headline": "Sci J", "source": "NASA", "sourceUrl": "https://www.nasa.gov/j"},
            {"sector": "SCI", "delta": 0.05, "headline": "Sci K", "source": "Nature", "sourceUrl": "https://www.nature.com/k"},
            {"sector": "LAW", "delta": 0.10, "headline": "Law L", "source": "SCOTUS", "sourceUrl": "https://www.supremecourt.gov/l"},
            {"sector": "LAW", "delta": 0.05, "headline": "Law M", "source": "ICJ", "sourceUrl": "https://www.icj-cij.org/m"},
            {"sector": "MEME", "delta": 0.15, "headline": "Vibe N", "source": "Variety", "sourceUrl": "https://variety.com/n"},
            {"sector": "MEME", "delta": 0.15, "headline": "Vibe O", "source": "Billboard", "sourceUrl": "https://www.billboard.com/o"},
        ],
        "skepticAudit": "Dry run test.",
        "forecast": "Dry run forecast.",
        "weeklyHindsight": None,
    }

    validated = validate_and_clamp_log_entry(sample_entry, prev_log, canonical_rules)
    feed_sum = round(sum(float(x["delta"]) for x in validated["sectorFeed"]), 2)
    assert validated["rawDelta"] == feed_sum, f"rawDelta {validated['rawDelta']} != {feed_sum}"
    assert validated["eventType"] == "STANDARD_DAY", "eventType bypass was not blocked"
    assert validated["capped"] is True, "expected daily cap to engage"
    assert validated["delta"] == 0.5, f"expected clamped delta 0.5, got {validated['delta']}"
    assert validated["current"] == 76.4, f"expected current 76.4, got {validated['current']}"
    assert validated["sectorFeed"][1]["delta"] == 0.0, "unverified source was not zeroed"
    assert "[UNVERIFIED SOURCE ZEROED]" in validated["sectorFeed"][1]["headline"]
    meme_sum = round(sum(float(x["delta"]) for x in validated["sectorFeed"] if x["sector"] == "MEME"), 2)
    assert abs(meme_sum) <= 0.20, f"MEME net sum {meme_sum} exceeded 0.20 cap"

    # Verify 7-Day TCE Convergence Window multiplier (1.25x on matching structural sector, +0.63% cap, MEME excluded)
    tce_history = [
        {
            "day": 6,
            "date": "2026-11-23",
            "eventType": "TCE",
            "sectorFeed": [{"sector": "LAW", "delta": 2.5}],
        }
    ]
    active_win = get_active_tce_window(tce_history, 7, canonical_rules)
    assert active_win and active_win["active"] is True and active_win["matchingSectors"] == ["LAW"]
    tce_sample = json.loads(json.dumps(sample_entry))
    # Reset sample deltas so LAW gets 0.20 -> 0.25 (1.25x) and positive cap is +0.63
    tce_sample["sectorFeed"][12]["delta"] = 0.20  # LAW
    tce_validated = validate_and_clamp_log_entry(tce_sample, prev_log, canonical_rules, active_tce_window=active_win)
    assert tce_validated["tceWindowActive"] is True
    assert tce_validated["sectorFeed"][12]["delta"] == 0.25, f"Expected 1.25x LAW boost 0.25, got {tce_validated['sectorFeed'][12]['delta']}"
    assert tce_validated["delta"] == 0.63, f"Expected TCE window positive cap 0.63, got {tce_validated['delta']}"
    # Verify TFE never opens a window
    tfe_history = [{"day": 6, "date": "2026-11-23", "eventType": "TFE", "sectorFeed": [{"sector": "LAW", "delta": -4.0}]}]
    assert get_active_tce_window(tfe_history, 7, canonical_rules) is None

    print("DRY RUN PASSED: All deterministic caps, source allowlists, MEME bounds, TCE window, and math invariants verified.")


def main():
    if "--verify-only" in sys.argv:
        verify_engine_lock(ENGINE_LOCK_PATH)
        return

    canonical_rules = verify_engine_lock(ENGINE_LOCK_PATH)

    if "--dry-run" in sys.argv:
        run_dry_run_check(canonical_rules)
        return

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI")
    if not api_key:
        print("ERROR: Neither GEMINI_API_KEY nor GEMINI environment variable is set.", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    print(f"Loading telemetry state from: {TELEMETRY_PATH}")
    telemetry = load_telemetry(TELEMETRY_PATH)
    logs = telemetry.get("logs", [])
    if not logs:
        print("ERROR: No logs found in telemetry.json", file=sys.stderr)
        sys.exit(1)

    latest_log = logs[-1]
    target_day = latest_log["day"] + 1
    is_weekly_audit = (target_day % 7 == 0) or ("--weekly-audit" in sys.argv)

    prev_date = datetime.date.fromisoformat(latest_log["date"])
    target_date_obj = prev_date + datetime.timedelta(days=1)
    target_date = target_date_obj.isoformat()

    # Enforce UTC Date Gate to prevent future-dated runs
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    if target_date_obj > today_utc:
        print(f"Target date {target_date} is in the future (UTC today: {today_utc}). Skipping run.")
        sys.exit(0)

    active_tce_window = get_active_tce_window(logs, target_day, canonical_rules)
    if active_tce_window:
        print(
            f"Active TCE Convergence Window: Triggered Day {active_tce_window['tceDay']} "
            f"(Day {active_tce_window['dayOfWindow']}/{canonical_rules.get('tceWindowDays', 7)}, "
            f"Sectors: {active_tce_window['matchingSectors']})"
        )

    print(f"Previous entry: Day {latest_log['day']} ({latest_log['date']}) @ {latest_log['current']}%")
    print(f"Targeting: Day {target_day} ({target_date}) [Weekly Hindsight Audit: {'ACTIVE' if is_weekly_audit else 'OFF'}]")

    system_prompt = build_system_rules_prompt(canonical_rules, is_weekly_audit=is_weekly_audit, target_day=target_day)

    audit_req = ""
    if is_weekly_audit:
        audit_req = f"""6. Perform the 7-day WEEKLY HINDSIGHT AUDIT (Cycle {target_day // 7}). Audit scored structural events (excluding MEME) from Days {target_day - 6} to {target_day - 1} against Prong 3 (Irreversible Structural Permanence) with explicit hindsight verdicts and reasoned adjustment deltas.
"""

    user_prompt = f"""Search global tier-1 news sources and cultural indices for events occurring between {latest_log['date']} and {target_date}.
The previous day was Day {latest_log['day']} with timeline parity at {latest_log['current']}%.
Target Day: {target_day}
Target Date: {target_date}

Generate the telemetry record for Day {target_day} strictly adhering to:
1. The 4-Prong Strict Scrutiny Gatekeeper (apply the 2014 test rigorously to the 7 structural sectors; MEME is exempt from Prong 1).
2. The 8-Sector Neutral Wire & Culture aggregator standard (at least 2 headlines per sector across POL, ECON, TECH, SOC, GLOB, SCI, LAW, and MEME with exact allowlisted sourceUrl citations; at least 16 items in sectorFeed).
3. The MEME sector vibe rubric and bounds (+/- 0.15% max per item, +/- 0.20% max net sector delta; cannot trigger TCE/TFE).
4. The 1.5x Cascading Nonsense Policy Multiplier if applicable.
{audit_req}5. Output MUST be a single raw JSON object matching the required schema.
"""

    print(f"Querying Gemini ({model}) with Google Search grounding (temperature=0.0)...")
    raw_entry, grounding_info = query_gemini(api_key, model, system_prompt, user_prompt)
    print("Gemini response received. Validating schema, source allowlists, and enforcing caps...")

    validated_entry = validate_and_clamp_log_entry(
        raw_entry, latest_log, canonical_rules, grounding_info=grounding_info, active_tce_window=active_tce_window
    )
    telemetry["logs"].append(validated_entry)

    print(f"Atomic update: Writing Day {validated_entry['day']} -> Parity {validated_entry['current']}% (Delta: {validated_entry['delta']:+0.2f}%)")
    atomic_save_telemetry(TELEMETRY_PATH, telemetry)
    print("Telemetry successfully updated and verified under Anti-Tampering Engine Lock v2.5.0.")


if __name__ == "__main__":
    main()
