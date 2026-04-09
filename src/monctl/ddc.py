from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional
import re

@dataclass(frozen=True)
class DdcResult:
    ok: bool
    message: str
    returncode: int
    stdout: str = ""
    stderr: str = ""


def set_input(bus: int, code: str, retries: int = 3) -> DdcResult:
    """
    Set input source using VCP 0x60. code must be like "0x11".
    Runs ddcutil synchronously (call this from a worker thread).
    """
    last: Optional[subprocess.CompletedProcess[str]] = None

    for _ in range(max(1, retries)):
        cp = subprocess.run(
            ["ddcutil", "-b", str(bus), "setvcp", "60", code, "--sleep-multiplier", "0.2"],
            text=True,
            capture_output=True,
        )
        last = cp
        if cp.returncode == 0:
            return DdcResult(True, f"Bus {bus} -> {code}", cp.returncode, cp.stdout, cp.stderr)

    assert last is not None
    msg = last.stderr.strip() or last.stdout.strip() or f"ddcutil failed (rc={last.returncode})"
    return DdcResult(False, msg, last.returncode, last.stdout, last.stderr)



def _normalize_to_hex(token: str) -> str:
    token = token.strip().lower()
    if token.startswith("0x"):
        return token
    return f"0x{int(token, 10):02x}"

def get_input(bus: int) -> DdcResult:
    """
    Returns DdcResult.message as a normalized hex code string like "0x11".
    Robust across different ddcutil output formats.
    """

    # Prefer terse output
    cp = subprocess.run(
        ["ddcutil", "-b", str(bus), "getvcp", "60", "--terse"],
        text=True,
        capture_output=True,
    )

    if cp.returncode == 0:
        s = (cp.stdout or "").strip()

        # Find all candidate tokens (hex or decimal)
        candidates = re.findall(r"(0x[0-9a-fA-F]+|\b\d+\b)", s)

        # Filter out the VCP code itself (60 / 0x60)
        filtered = [c for c in candidates if c.lower() not in ("60", "0x60")]

        if filtered:
            val = filtered[-1]  # usually last is the current value
            return DdcResult(True, _normalize_to_hex(val), 0, cp.stdout, cp.stderr)

        # If we get here, terse output didn't include a usable value
        # fall through to non-terse parsing

    # Fallback: normal output
    cp = subprocess.run(
        ["ddcutil", "-b", str(bus), "getvcp", "60"],
        text=True,
        capture_output=True,
    )
    if cp.returncode != 0:
        msg = cp.stderr.strip() or cp.stdout.strip() or f"ddcutil failed (rc={cp.returncode})"
        return DdcResult(False, msg, cp.returncode, cp.stdout, cp.stderr)

    out = cp.stdout or ""

    # Accept both:
    # "current value = 0x11"
    # "current value = 17"
    m = re.search(r"current value\s*=\s*(0x[0-9a-fA-F]+|\d+)", out, re.IGNORECASE)
    if m:
        return DdcResult(True, _normalize_to_hex(m.group(1)), 0, cp.stdout, cp.stderr)

    # Last ditch: any hex literal (but avoid 0x60 if that's all we find)
    hexes = [h.lower() for h in re.findall(r"(0x[0-9a-fA-F]+)", out)]
    hexes = [h for h in hexes if h != "0x60"]
    if hexes:
        return DdcResult(True, hexes[-1], 0, cp.stdout, cp.stderr)

    return DdcResult(False, f"Could not parse current input. Output: {out.strip()}", 0, cp.stdout, cp.stderr)
