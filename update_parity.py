#!/usr/bin/env python3
"""
The Picard Index — Autonomous Telemetry Engine & Schema Validator
7-Sector Aggregator with Anti-Tampering Engine Lock Enforcement.
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


def verify_engine_lock(lock_path: str) -> dict:
    """Verifies SHA-256 integrity of canonical rules to prevent unauthorized parameter tampering."""
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
    
    print(f"Anti-Tampering Engine Lock verified. Checksum: {computed_sha[:16]}...")
    return canonical_rules


def build_system_rules_prompt(rules: dict) -> str:
    pfa_base = rules.get("pfaBaseline", 75.0)
    daily_cap = rules.get("standardDailyCap", 0.5)
    meme_cap = rules.get("memeSectorMaxItemDelta", 0.15)
    mult = rules.get("cascadingNonsenseMultiplier", 1.5)
    
    return f"""You are the autonomous telemetry engine for The Picard Index (Temporal Parity & Reality Audit).
Your role is to ingest the past 24 hours of global news, evaluate it under strict temporal audit rules, and produce the next day's telemetry entry in valid JSON format.

--- CANONICAL ENGINE RULES (LOCKED v2.1.0) ---
- Sovereign Anchor: Picard's Final Act (PFA) on 2026-10-28 set a non-repeatable dynamic sovereign baseline at {pfa_base}%.
- Baseline Waterline: {pfa_base}%.
- Standard daily cap: Delta is strictly capped between -{daily_cap}% and +{daily_cap}%. Low signal days hold at 0.0% (Noise Floor).
- 1.5x Cascading Nonsense Policy Multiplier: Contradictory policies receive a {mult}x negative drag (-0.25% to -0.75% base) if cleared by Strict Scrutiny.

--- 4-PRONG STRICT SCRUTINY GATEKEEPER ---
Any candidate attempting to bypass the +/-{daily_cap}% daily cap (such as a Temporal Convergence Event +2.0% to +5.0%, or Temporal Fracture Event -3.0% to -15.0%) MUST CLEAR ALL FOUR PRONGS. Failing even one prong downgrades the event to capped daily scoring (<= +/-{daily_cap}%) or 0.0%:
1. Prong 1 — The 2014 Test (Baseline Survival Filter): Would this qualify as normal constitutional governance, routine election turnover, standard court procedure, or ordinary market fluctuation in 2014? If yes -> automatic 0.0% (no bonus points for baseline survival; no panic multiplier for routine political friction).
2. Prong 2 — Causal Independence (No Double-Counting): Is this an independent structural catalyst or rupture, or merely a predictable second-order reaction to an already-scored event?
3. Prong 3 — Irreversible Structural Permanence: Does it enact binding law, permanent structural reform, or irreversible systemic fallout—rather than a committee vote, PR pledge, temporary executive order, or 24-hour outrage cycle?
4. Prong 4 — Multi-Outlet Empirical Verification: Confirmed across 2+ independent major neutral tier-1 outlets with measurable real-world impact.

--- 7-SECTOR NEUTRAL WIRE & CULTURE AGGREGATOR ---
You must evaluate and cite at least 2 verified headlines per sector (at least 14 items total in sectorFeed) with tier-1 source citations (Reuters, AP, AFP, Bloomberg, BBC News, NPR, PBS, NASA, ESA, Nature, ICJ, Variety, Billboard):
- POL: Political & Institutional
- ECON: Economic & Markets
- TECH: Technology & AI
- SOC: Social & Cultural
- GLOB: Global & Geopolitical
- SCI: Science & Environment
- MEME: Pop & Internet Culture (viral cultural phenomena, box office / entertainment milestones, major meme realignments). SUB-CAP: Each MEME item delta must be strictly bounded to +/-{meme_cap}%. MEME events CANNOT trigger a TCE or TFE.

--- REQUIRED JSON OUTPUT SCHEMA ---
Output ONLY a single valid JSON object representing the new log entry with EXACTLY these fields:
{{
  "day": <integer: next day number>,
  "date": "<YYYY-MM-DD: date of target day>",
  "label": "<UPPERCASE SHORT SUMMARY: e.g. DAY N: TOP TOPIC & TOP TOPIC>",
  "eventType": "STANDARD_DAY",
  "previous": <float: previous day parity>,
  "current": <float: previous + delta, rounded to 2 decimals>,
  "delta": <float: net delta clamped to [-{daily_cap}, +{daily_cap}] unless all 4 prongs cleared>,
  "rawDelta": <float: unclamped sum of sector contributions>,
  "capped": <boolean: true if rawDelta exceeded cap and was clamped>,
  "capLimit": {daily_cap},
  "echoes": [<array of string echo watchlist triggers if applicable>],
  "realignment": [<array of string positive realignment items with format: "+X.XX% [SECTOR] Headline — (Source: Wire)">],
  "anomalies": [<array of string negative anomaly items with format: "-X.XX% [SECTOR] Headline — (Source: Wire)">],
  "sectorFeed": [
    {{ "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>" }},
    {{ "sector": "MEME", "delta": <float between -{meme_cap} and +{meme_cap}>, "headline": "<text>", "source": "<wire/source>" }},
    {{ "sector": "MEME", "delta": <float between -{meme_cap} and +{meme_cap}>, "headline": "<text>", "source": "<wire/source>" }}
  ],
  "skepticAudit": "<text: detailed strict scrutiny analysis explaining why events passed or failed prongs>",
  "forecast": "<text: concise synthesis and outlook relative to the {pfa_base}% Picard Standard baseline>"
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


def query_gemini_single_attempt(api_key: str, model: str, system_prompt: str, user_prompt: str, use_json_mime: bool = True) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt},
                    {"text": user_prompt}
                ]
            }
        ],
        "tools": [
            {"googleSearch": {}}
        ]
    }
    if use_json_mime:
        payload["generationConfig"] = {
            "responseMimeType": "application/json"
        }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=120) as resp:
        resp_body = resp.read().decode("utf-8")
        result = json.loads(resp_body)

    try:
        candidate = result["candidates"][0]
        text_content = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Malformed Gemini API response: {result}") from e

    clean_json = text_content.strip()
    if clean_json.startswith("```"):
        clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
        clean_json = re.sub(r"\s*```$", "", clean_json)

    try:
        return json.loads(clean_json)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text_content)
        if match:
            return json.loads(match.group(0))
        raise


def query_gemini(api_key: str, requested_model: str, system_prompt: str, user_prompt: str) -> dict:
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


def validate_and_clamp_log_entry(entry: dict, previous_log: dict, canonical_rules: dict) -> dict:
    required_keys = [
        "day", "date", "label", "eventType", "previous", "current",
        "delta", "rawDelta", "capped", "capLimit", "echoes",
        "realignment", "anomalies", "sectorFeed", "skepticAudit", "forecast"
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

    # 7-Sector Feed Validation
    sector_feed = entry.get("sectorFeed", [])
    required_sectors = set(canonical_rules.get("requiredSectors", ["POL", "ECON", "TECH", "SOC", "GLOB", "SCI", "MEME"]))
    sectors_present = {item.get("sector") for item in sector_feed}
    
    if not required_sectors.issubset(sectors_present):
        missing = required_sectors - sectors_present
        raise ValueError(f"Sector feed missing required sectors: {missing}")

    # Enforce MEME sector sub-cap (+/- 0.15% max per item)
    meme_item_cap = float(canonical_rules.get("memeSectorMaxItemDelta", 0.15))
    for item in sector_feed:
        if item.get("sector") == "MEME":
            raw_val = float(item.get("delta", 0.0))
            clamped_val = max(-meme_item_cap, min(meme_item_cap, raw_val))
            item["delta"] = round(clamped_val, 2)

    # Count items per sector
    min_items = int(canonical_rules.get("minItemsPerSector", 2))
    sector_counts = {}
    for item in sector_feed:
        s = item.get("sector")
        sector_counts[s] = sector_counts.get(s, 0) + 1
    
    for req_sec in required_sectors:
        if sector_counts.get(req_sec, 0) < min_items:
            print(f"Warning: Sector {req_sec} has fewer than {min_items} items (has {sector_counts.get(req_sec, 0)})")

    # Enforce standard daily cap unless explicit override cleared
    event_type = entry.get("eventType", "STANDARD_DAY")
    cap_limit = float(canonical_rules.get("standardDailyCap", 0.5))
    raw_delta = float(entry.get("rawDelta", entry.get("delta", 0.0)))
    
    if event_type == "STANDARD_DAY":
        if raw_delta > cap_limit:
            delta = cap_limit
            capped = True
        elif raw_delta < -cap_limit:
            delta = -cap_limit
            capped = True
        else:
            delta = round(raw_delta, 2)
            capped = False
    else:
        # Non-standard days must still be bounded between -15.0 and +5.0
        delta = max(-15.0, min(5.0, round(raw_delta, 2)))
        capped = False

    entry["delta"] = delta
    entry["rawDelta"] = round(raw_delta, 2)
    entry["capped"] = capped
    entry["capLimit"] = cap_limit
    
    new_current = round(prev_current + delta, 2)
    new_current = max(0.0, min(100.0, new_current))
    entry["current"] = new_current

    return entry


def main():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI")
    if not api_key:
        print("ERROR: Neither GEMINI_API_KEY nor GEMINI environment variable is set.", file=sys.stderr)
        sys.exit(1)

    # 1. Enforce Anti-Tampering Engine Lock
    canonical_rules = verify_engine_lock(ENGINE_LOCK_PATH)

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    print(f"Loading telemetry state from: {TELEMETRY_PATH}")
    telemetry = load_telemetry(TELEMETRY_PATH)
    logs = telemetry.get("logs", [])
    if not logs:
        print("ERROR: No logs found in telemetry.json", file=sys.stderr)
        sys.exit(1)

    latest_log = logs[-1]
    target_day = latest_log["day"] + 1
    
    prev_date = datetime.date.fromisoformat(latest_log["date"])
    target_date = (prev_date + datetime.timedelta(days=1)).isoformat()

    print(f"Previous entry: Day {latest_log['day']} ({latest_log['date']}) @ {latest_log['current']}%")
    print(f"Targeting: Day {target_day} ({target_date})")

    system_prompt = build_system_rules_prompt(canonical_rules)

    user_prompt = f"""Search global tier-1 news sources and cultural indices for events occurring between {latest_log['date']} and {target_date}.
The previous day was Day {latest_log['day']} with timeline parity at {latest_log['current']}%.
Target Day: {target_day}
Target Date: {target_date}

Generate the telemetry record for Day {target_day} strictly adhering to:
1. The 4-Prong Strict Scrutiny Gatekeeper (apply the 2014 test rigorously).
2. The 7-Sector Neutral Wire & Culture aggregator standard (at least 2 headlines per sector across POL, ECON, TECH, SOC, GLOB, SCI, and MEME with citations; at least 14 items in sectorFeed).
3. The MEME sector item delta sub-cap (+/- 0.15% max per item; cannot trigger TCE/TFE).
4. The 1.5x Cascading Nonsense Policy Multiplier if applicable.
5. Output MUST be a single raw JSON object matching the required schema.
"""

    print(f"Querying Gemini ({model}) with Google Search grounding...")
    raw_entry = query_gemini(api_key, model, system_prompt, user_prompt)
    print("Gemini response received. Validating schema and enforcing caps...")

    validated_entry = validate_and_clamp_log_entry(raw_entry, latest_log, canonical_rules)
    telemetry["logs"].append(validated_entry)

    print(f"Atomic update: Writing Day {validated_entry['day']} -> Parity {validated_entry['current']}% (Delta: {validated_entry['delta']:+0.2f}%)")
    atomic_save_telemetry(TELEMETRY_PATH, telemetry)
    print("Telemetry successfully updated and verified under Anti-Tampering Engine Lock v2.1.0.")


if __name__ == "__main__":
    main()
