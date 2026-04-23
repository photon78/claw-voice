#!/usr/bin/env python3
"""
send_discord.py — Send an OGG file as a Discord audio message via webhook.

No dependencies beyond Python stdlib.

⚠️  UNTESTED — feature branch only

Usage:
  python3 send_discord.py /tmp/output.ogg
  python3 send_discord.py /tmp/output.ogg --content "Agent speaking"

Token/webhook resolution order:
  1. DISCORD_WEBHOOK_URL environment variable
  2. ~/.openclaw/.env file
"""

import argparse
import json
import os
import sys
from pathlib import Path


def _load_env_file(env_path: Path) -> dict:
    """Parse a simple KEY=VALUE .env file."""
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def send_discord(ogg_path: Path, webhook_url: str, content: str | None = None) -> dict:
    """Upload OGG file as Discord audio attachment via webhook. Returns API response dict."""
    import urllib.request

    boundary = "----ClawVoiceDiscordBoundary"

    def _field(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    parts: list[bytes] = []

    # Optional text content
    if content:
        payload = json.dumps({"content": content}).encode("utf-8")
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="payload_json"\r\n'
                f"Content-Type: application/json\r\n\r\n"
            ).encode("utf-8")
            + payload
            + b"\r\n"
        )

    # Audio file
    data = ogg_path.read_bytes()
    parts.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{ogg_path.name}"\r\n'
            f"Content-Type: audio/ogg\r\n\r\n"
        ).encode("utf-8")
        + data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {"ok": True}


def main():
    parser = argparse.ArgumentParser(description="Send OGG file as Discord audio via webhook")
    parser.add_argument("ogg", help="Path to .ogg file")
    parser.add_argument("--content", help="Optional text message alongside the audio")
    args = parser.parse_args()

    ogg_path = Path(args.ogg)
    if not ogg_path.exists():
        print(f"ERROR: File not found: {ogg_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve webhook URL
    env_file = _load_env_file(Path.home() / ".openclaw" / ".env")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or env_file.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print(
            "ERROR: DISCORD_WEBHOOK_URL not found.\n"
            "  Set it as environment variable or add to ~/.openclaw/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    result = send_discord(ogg_path, webhook_url, args.content)
    if result.get("ok", True):
        print("Sent to Discord.")
    else:
        print(f"Discord webhook error: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
