#!/usr/bin/env python3
"""
The Picard Index — Canonical Attestation Signer
Signs engine_lock.json, update_parity.py, and telemetry.json with ECDSA P-256 (SHA-256)
using the PICARD_SIGNING_KEY environment variable (PEM private key).
"""

import base64
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CANONICAL_REPO = "joeripari-lab/picard-index"
FILES_TO_HASH = {
    "engineLockFileSha256": "engine_lock.json",
    "updateParitySha256": "update_parity.py",
    "telemetrySha256": "telemetry.json",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_openssl() -> str:
    exe = shutil.which("openssl")
    if exe:
        return exe
    win_git_openssl = r"C:\Program Files\Git\usr\bin\openssl.exe"
    if os.path.exists(win_git_openssl):
        return win_git_openssl
    raise RuntimeError("openssl binary not found on PATH.")


def der_sig_to_p1363(der_bytes: bytes) -> bytes:
    """Convert ASN.1 DER ECDSA signature (SEQUENCE { INTEGER r, INTEGER s }) to 64-byte IEEE P1363 (r || s)."""
    if len(der_bytes) < 8 or der_bytes[0] != 0x30:
        raise ValueError("Invalid DER signature header")
    idx = 2
    if der_bytes[1] & 0x80:
        idx += der_bytes[1] & 0x7F

    def read_int(pos: int) -> tuple[bytes, int]:
        if der_bytes[pos] != 0x02:
            raise ValueError("Expected INTEGER tag in DER signature")
        length = der_bytes[pos + 1]
        val = der_bytes[pos + 2 : pos + 2 + length]
        val = val.lstrip(b"\x00")
        if len(val) > 32:
            raise ValueError("ECDSA P-256 integer exceeds 32 bytes")
        return val.rjust(32, b"\x00"), pos + 2 + length

    r, idx = read_int(idx)
    s, idx = read_int(idx)
    return r + s


def compute_public_key_fingerprint(openssl_bin: str, pub_pem_path: str) -> str:
    """Compute SHA-256 fingerprint of the DER-encoded SubjectPublicKeyInfo (SPKI)."""
    proc = subprocess.run(
        [openssl_bin, "pkey", "-pubin", "-in", pub_pem_path, "-outform", "DER"],
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(proc.stdout).hexdigest()


def build_payload(pub_fingerprint: str) -> dict:
    with open(os.path.join(BASE_DIR, "engine_lock.json"), "r", encoding="utf-8") as f:
        lock_data = json.load(f)
    engine_rules_sha = hashlib.sha256(
        json.dumps(lock_data["canonicalRules"], sort_keys=True).encode("utf-8")
    ).hexdigest()

    with open(os.path.join(BASE_DIR, "telemetry.json"), "r", encoding="utf-8") as f:
        telemetry = json.load(f)
    latest_log = telemetry["logs"][-1]

    hashes = {"engineLockSha256": engine_rules_sha}
    for key, filename in FILES_TO_HASH.items():
        hashes[key] = sha256_file(os.path.join(BASE_DIR, filename))

    return {
        "schemaVersion": "1.0.0",
        "canonicalRepo": CANONICAL_REPO,
        "algorithm": "ECDSA-P256-SHA256",
        "keyFingerprint": pub_fingerprint,
        "signedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": latest_log["day"],
        "date": latest_log["date"],
        "parity": latest_log["current"],
        "hashes": hashes,
    }


def canonical_payload_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main():
    private_pem = os.environ.get("PICARD_SIGNING_KEY", "").strip()
    if not private_pem:
        print("PICARD_SIGNING_KEY is not set; skipping cryptographic attestation.", file=sys.stderr)
        sys.exit(2)

    openssl_bin = find_openssl()
    pub_pem_path = os.path.join(BASE_DIR, "picard_public.pem")

    with tempfile.TemporaryDirectory() as tmpdir:
        priv_path = os.path.join(tmpdir, "priv.pem")
        with open(priv_path, "w", encoding="utf-8") as f:
            f.write(private_pem + "\n")

        # Derive public key from private key and write/verify picard_public.pem
        derived_pub_path = os.path.join(tmpdir, "pub.pem")
        subprocess.run(
            [openssl_bin, "pkey", "-in", priv_path, "-pubout", "-out", derived_pub_path],
            check=True,
            capture_output=True,
        )
        with open(derived_pub_path, "r", encoding="utf-8") as f:
            derived_pub_pem = f.read()

        if os.path.exists(pub_pem_path):
            with open(pub_pem_path, "r", encoding="utf-8") as f:
                existing_pub_pem = f.read()
            if existing_pub_pem.strip() != derived_pub_pem.strip():
                raise RuntimeError(
                    "PICARD_SIGNING_KEY does not match committed picard_public.pem! Refusing to sign."
                )
        else:
            with open(pub_pem_path, "w", encoding="utf-8") as f:
                f.write(derived_pub_pem)
            print(f"Wrote public key to {pub_pem_path}")

        pub_fingerprint = compute_public_key_fingerprint(openssl_bin, derived_pub_path)
        payload = build_payload(pub_fingerprint)
        payload_bytes = canonical_payload_bytes(payload)

        payload_file = os.path.join(tmpdir, "payload.json")
        sig_der_file = os.path.join(tmpdir, "sig.der")
        with open(payload_file, "wb") as f:
            f.write(payload_bytes)

        subprocess.run(
            [openssl_bin, "dgst", "-sha256", "-sign", priv_path, "-out", sig_der_file, payload_file],
            check=True,
            capture_output=True,
        )
        with open(sig_der_file, "rb") as f:
            der_bytes = f.read()

        raw_p1363_bytes = der_sig_to_p1363(der_bytes)

    attestation = {
        "payload": payload,
        "signature": base64.b64encode(raw_p1363_bytes).decode("ascii"),
        "signatureDer": base64.b64encode(der_bytes).decode("ascii"),
    }

    att_path = os.path.join(BASE_DIR, "attestation.json")
    with open(att_path, "w", encoding="utf-8") as f:
        json.dump(attestation, f, indent=2)
        f.write("\n")

    print(f"Signed attestation.json for Day {payload['day']} ({payload['parity']}%)")
    print(f"Key Fingerprint: {pub_fingerprint}")


if __name__ == "__main__":
    main()
