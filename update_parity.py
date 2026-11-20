#!/usr/bin/env python3
"""
The Picard Index — Autonomous Telemetry Engine & Schema Validator
Serverless pipeline: Queries Gemini API with Google Search grounding, applies
the 4-Prong Strict Scrutiny Gatekeeper and 6-Sector Neutral Wire standards,
validates schema bounds, and atomically updates telemetry.json.
"""

import datetime
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

TELEMETRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telemetry.json")
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_RULES_PROMPT = """You are the autonomous telemetry engine for The Picard Index (Temporal Parity & Reality Audit).
Your role is to ingest the past 24 hours of global news, evaluate it under strict temporal audit rules, and produce the next day's telemetry entry in valid JSON format.

--- CORE AXIOMS ---
- Sovereign Anchor: Picard's Final Act (PFA) on 2026-10-28 set a non-repeatable dynamic sovereign baseline at 75.0% (The Picard Standard).
- Baseline Waterline: 75.0%. Reality before PFA was 7.5%.
- Current monitoring mode: STANDARD_DAY.
- Standard daily cap: Delta is strictly capped between -0.5% and +0.5%. Low signal days hold at 0.0% (Noise Floor).

--- 4-PRONG STRICT SCRUTINY GATEKEEPER ---
Any candidate attempting to bypass the +/-0.5% daily cap (such as a Temporal Convergence Event +2.0% to +5.0%, or Temporal Fracture Event -3.0% to -15.0%) MUST CLEAR ALL FOUR PRONGS. Failing even one prong downgrades the event to capped daily scoring (<= +/-0.5%) or 0.0%:
1. Prong 1 — The 2014 Test (Baseline Survival Filter): Would this qualify as normal constitutional governance, routine election turnover, standard court procedure, or ordinary market fluctuation in 2014? If yes -> automatic 0.0% (no bonus points for baseline survival; no panic multiplier for routine political friction).
2. Prong 2 — Causal Independence (No Double-Counting): Is this an independent structural catalyst or rupture, or merely a predictable second-order reaction to an already-scored event?
3. Prong 3 — Irreversible Structural Permanence: Does it enact binding law, permanent structural reform, or irreversible systemic fallout—rather than a committee vote, PR pledge, temporary executive order, or 24-hour outrage cycle?
4. Prong 4 — Multi-Outlet Empirical Verification: Confirmed across 2+ independent major neutral tier-1 outlets with measurable real-world impact.

--- 1.5x CASCADING NONSENSE POLICY MULTIPLIER ---
Self-defeating, administratively contradictory policies triggering multi-sector legal, diplomatic, or economic fallout receive a 1.5x negative weight multiplier (-0.25% to -0.75% base drag) if cleared by Strict Scrutiny.

--- 6-SECTOR NEUTRAL WIRE AGGREGATOR STANDARD ---
You must evaluate and cite at least 2 verified headlines per sector (12 items total in sectorFeed) with tier-1 neutral wire / institutional citations (Reuters, AP, AFP, Bloomberg, BBC News, NPR, PBS, NASA, ESA, Nature, ICJ):
- POL: Political & Institutional
- ECON: Economic & Markets
- TECH: Technology & AI
- SOC: Social & Cultural
- GLOB: Global & Geopolitical
- SCI: Science & Environment

--- REQUIRED JSON OUTPUT SCHEMA ---
Output ONLY a single valid JSON object representing the new log entry with EXACTLY these fields:
{
  "day": <integer: next day number>,
  "date": "<YYYY-MM-DD: date of target day>",
  "label": "<UPPERCASE SHORT SUMMARY: e.g. DAY N: TOP TOPIC & TOP TOPIC>",
  "eventType": "STANDARD_DAY",
  "previous": <float: previous day parity>,
  "current": <float: previous + delta, rounded to 2 decimals>,
  "delta": <float: net delta clamped to [-0.5, +0.5] unless all 4 prongs cleared>,
  "rawDelta": <float: unclamped sum of sector contributions>,
  "capped": <boolean: true if rawDelta exceeded cap and was clamped>,
  "capLimit": 0.5,
  "echoes": [<array of string echo watchlist triggers if applicable>],
  "realignment": [<array of string positive realignment items with format: "+X.XX% [SECTOR] Headline — (Source: Wire)">],
  "anomalies": [<array of string negative anomaly items with format: "-X.XX% [SECTOR] Headline — (Source: Wire)">],
  "sectorFeed": [
    { "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "POL", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "ECON", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "TECH", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "SOC", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "GLOB", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>" },
    { "sector": "SCI", "delta": <float>, "headline": "<text>", "source": "<wire>" }
  ],
  "skepticAudit": "<text: detailed strict scrutiny analysis explaining why events passed or failed prongs>",
  "forecast": "<text: concise synthesis and outlook relative to the 75.0% Picard Standard baseline>"
}
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


def query_gemini(api_key: str, model: str, user_prompt: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_RULES_PROMPT},
                    {"text": user_prompt}
                ]
            }
        ],
        "tools": [
            {"googleSearch": {}}
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_body = resp.read().decode("utf-8")
            result = json.loads(resp_body)
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Gemini API HTTP {e.code}: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Gemini API request failed: {e}")

    try:
        candidate = result["candidates"][0]
        text_content = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Malformed Gemini API response: {result}") from e

    # Extract clean JSON
    clean_json = text_content.strip()
    if clean_json.startswith("```"):
        clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
        clean_json = re.sub(r"\s*```$", "", clean_json)
    
    return json.loads(clean_json)


def validate_and_clamp_log_entry(entry: dict, previous_log: dict) -> dict:
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

    # Sector feed check
    sectors = {item.get("sector") for item in entry.get("sectorFeed", [])}
    required_sectors = {"POL", "ECON", "TECH", "SOC", "GLOB", "SCI"}
    if not required_sectors.issubset(sectors):
        missing = required_sectors - sectors
        raise ValueError(f"Sector feed missing required sectors: {missing}")

    # Enforce standard daily cap unless explicit override cleared
    event_type = entry.get("eventType", "STANDARD_DAY")
    cap_limit = float(entry.get("capLimit", 0.5))
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
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
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
    
    prev_date = datetime.date.fromisoformat(latest_log["date"])
    target_date = (prev_date + datetime.timedelta(days=1)).isoformat()

    print(f"Previous entry: Day {latest_log['day']} ({latest_log['date']}) @ {latest_log['current']}%")
    print(f"Targeting: Day {target_day} ({target_date})")

    user_prompt = f"""Search global tier-1 news sources for events occurring between {latest_log['date']} and {target_date}.
The previous day was Day {latest_log['day']} with timeline parity at {latest_log['current']}%.
Target Day: {target_day}
Target Date: {target_date}

Generate the telemetry record for Day {target_day} strictly adhering to:
1. The 4-Prong Strict Scrutiny Gatekeeper (apply the 2014 test rigorously).
2. The 6-Sector Neutral Wire aggregator standard (at least 2 headlines per sector across POL, ECON, TECH, SOC, GLOB, SCI with wire source citations).
3. The 1.5x Cascading Nonsense Policy Multiplier if applicable.
4. Output MUST be a single raw JSON object matching the required schema.
"""

    print(f"Querying Gemini ({model}) with Google Search grounding...")
    raw_entry = query_gemini(api_key, model, user_prompt)
    print("Gemini response received. Validating schema and enforcing caps...")

    validated_entry = validate_and_clamp_log_entry(raw_entry, latest_log)
    telemetry["logs"].append(validated_entry)

    print(f"Atomic update: Writing Day {validated_entry['day']} -> Parity {validated_entry['current']}% (Delta: {validated_entry['delta']:+0.2f}%)")
    atomic_save_telemetry(TELEMETRY_PATH, telemetry)
    print("Telemetry successfully updated and verified.")


if __name__ == "__main__":
    main()
