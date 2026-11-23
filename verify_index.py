#!/usr/bin/env python3
"""
The Picard Index — Public Provenance & Integrity Verifier
Independently verifies that a local repository or hosted Picard Index site
matches the canonical cryptographic signature of joeripari-lab/picard-index.

Usage:
  python verify_index.py
  python verify_index.py --url https://joeripari-lab.github.io/picard-index
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pin the canonical key fingerprint so clones cannot silently swap picard_public.pem.
EXPECTED_KEY_FINGERPRINT = "3f7655b2c4ca6b5560a4c673befef86cfe5b8ddd86f412e784ce39723d8a567c"


def find_openssl() -> str | None:
    exe = shutil.which("openssl")
    if exe:
        return exe
    win_git_openssl = r"C:\Program Files\Git\usr\bin\openssl.exe"
    if os.path.exists(win_git_openssl):
        return win_git_openssl
    return None


def fetch_bytes(source_url: str | None, filename: str) -> bytes:
    if source_url:
        url = source_url.rstrip("/") + "/" + filename
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    path = os.path.join(BASE_DIR, filename)
    with open(path, "rb") as f:
        return f.read()


def compute_public_key_fingerprint(openssl_bin: str, pub_pem_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        tmp.write(pub_pem_bytes)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [openssl_bin, "pkey", "-pubin", "-in", tmp_path, "-outform", "DER"],
            capture_output=True,
            check=True,
        )
        return hashlib.sha256(proc.stdout).hexdigest()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def verify_signature_openssl(openssl_bin: str, pub_pem_bytes: bytes, payload_bytes: bytes, sig_der_bytes: bytes) -> bool:
    with tempfile.TemporaryDirectory() as tmpdir:
        pub_path = os.path.join(tmpdir, "pub.pem")
        payload_path = os.path.join(tmpdir, "payload.json")
        sig_path = os.path.join(tmpdir, "sig.der")
        with open(pub_path, "wb") as f:
            f.write(pub_pem_bytes)
        with open(payload_path, "wb") as f:
            f.write(payload_bytes)
        with open(sig_path, "wb") as f:
            f.write(sig_der_bytes)

        proc = subprocess.run(
            [openssl_bin, "dgst", "-sha256", "-verify", pub_path, "-signature", sig_path, payload_path],
            capture_output=True,
        )
        return proc.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Verify Picard Index cryptographic provenance.")
    parser.add_argument("--url", help="Base URL of a hosted Picard Index instance to verify remotely.")
    args = parser.parse_args()

    errors = []

    try:
        lock_bytes = fetch_bytes(args.url, "engine_lock.json")
        parity_bytes = fetch_bytes(args.url, "update_parity.py")
        telemetry_bytes = fetch_bytes(args.url, "telemetry.json")
        attestation_bytes = fetch_bytes(args.url, "attestation.json")
        pub_pem_bytes = fetch_bytes(args.url, "picard_public.pem")
    except Exception as e:
        print(f"FAIL: Could not load required provenance files: {e}", file=sys.stderr)
        sys.exit(1)

    lock_data = json.loads(lock_bytes.decode("utf-8"))
    computed_rules_sha = hashlib.sha256(
        json.dumps(lock_data["canonicalRules"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    if computed_rules_sha != lock_data.get("engineSha256"):
        errors.append(
            f"engine_lock.json rules mismatch: expected {lock_data.get('engineSha256')}, got {computed_rules_sha}"
        )

    if not args.url and lock_data.get("promptTemplateSha256"):
        import update_parity
        computed_prompt_sha = update_parity.compute_prompt_template_sha256(lock_data["canonicalRules"])
        if computed_prompt_sha != lock_data.get("promptTemplateSha256"):
            errors.append(
                f"promptTemplateSha256 mismatch: expected {lock_data.get('promptTemplateSha256')}, got {computed_prompt_sha}"
            )

    attestation = json.loads(attestation_bytes.decode("utf-8"))
    payload = attestation.get("payload", {})
    hashes = payload.get("hashes", {})

    actual_hashes = {
        "engineLockSha256": computed_rules_sha,
        "engineLockFileSha256": hashlib.sha256(lock_bytes).hexdigest(),
        "updateParitySha256": hashlib.sha256(parity_bytes).hexdigest(),
        "telemetrySha256": hashlib.sha256(telemetry_bytes).hexdigest(),
    }

    for k, actual in actual_hashes.items():
        expected = hashes.get(k)
        if expected != actual:
            errors.append(f"Hash mismatch for {k}: attestation has {expected}, actual is {actual}")

    openssl_bin = find_openssl()
    if not openssl_bin:
        print("FAIL: openssl binary is required to verify ECDSA P-256 signature.", file=sys.stderr)
        sys.exit(1)

    pub_fp = compute_public_key_fingerprint(openssl_bin, pub_pem_bytes)
    if payload.get("keyFingerprint") != pub_fp:
        errors.append(
            f"Public key fingerprint mismatch: attestation claims {payload.get('keyFingerprint')}, key is {pub_fp}"
        )
    if EXPECTED_KEY_FINGERPRINT and pub_fp != EXPECTED_KEY_FINGERPRINT:
        errors.append(
            f"UNTRUSTED KEY: Key fingerprint {pub_fp} does not match official pinned key {EXPECTED_KEY_FINGERPRINT}"
        )

    sig_der_b64 = attestation.get("signatureDer")
    if not sig_der_b64:
        errors.append("attestation.json missing 'signatureDer'")
    else:
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig_der_bytes = base64.b64decode(sig_der_b64)
        if not verify_signature_openssl(openssl_bin, pub_pem_bytes, payload_bytes, sig_der_bytes):
            errors.append("INVALID ECDSA SIGNATURE: attestation.json was not signed by picard_public.pem")

    if errors:
        print("VERIFICATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("VERIFIED CANONICAL PICARD INDEX")
    print(f"  Repo:            {payload.get('canonicalRepo')}")
    print(f"  Day / Parity:    Day {payload.get('day')} ({payload.get('date')}) @ {payload.get('parity')}%")
    print(f"  Signed At:       {payload.get('signedAt')}")
    print(f"  Key Fingerprint: {pub_fp}")


if __name__ == "__main__":
    main()
