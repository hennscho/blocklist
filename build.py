#!/usr/bin/env python3
"""
Fuehrt mehrere Upstream-Allowlists zu einer Technitium-tauglichen Datei zusammen.

- laedt alle URLs aus sources.txt
- normalisiert hosts-Format, Adblock-Format (@@||domain^) und Plain-Domains
- verwirft Regex-/Wildcard-Zeilen (Technitium kann damit in Allow-Lists nichts anfangen)
- zieht alles ab, was in quarantine.txt steht
- haengt allowlist-local.txt an (die gewinnt immer)
- schreibt allowlist.txt sortiert und dedupliziert

Aufruf: python3 build.py
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / "sources.txt"
QUARANTINE = ROOT / "quarantine.txt"
LOCAL = ROOT / "allowlist-local.txt"
OUTPUT = ROOT / "allowlist.txt"

USER_AGENT = "dns-allowlist-build/1.0 (+https://github.com/)"
TIMEOUT = 60

# Ein Label: a-z 0-9 und Bindestrich, nicht am Rand. Mindestens zwei Labels.
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}$"
)

# Zeilen, die wir bewusst nicht uebernehmen.
REGEXISH = re.compile(r"[()\[\]|^$*?\\/+]")


def read_list_file(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize(raw_line: str) -> str | None:
    """Eine Rohzeile -> Domain oder None."""
    line = raw_line.strip()
    if not line:
        return None

    # Kommentare: #, !, // ... aber Adblock-Ausnahmen (@@) erst auswerten.
    if line.startswith(("#", "//", ";")):
        return None
    if line.startswith("!"):
        return None

    # Adblock-Ausnahmeregel: @@||example.com^ / @@||example.com^$important
    if line.startswith("@@"):
        line = line[2:]
        line = line.lstrip("|")
        line = line.split("^", 1)[0]
        line = line.split("$", 1)[0]
    elif line.startswith("||"):
        line = line[2:].split("^", 1)[0].split("$", 1)[0]

    # hosts-Format: 0.0.0.0 example.com / 127.0.0.1 example.com
    parts = line.split()
    if len(parts) >= 2 and re.match(r"^(\d{1,3}\.){3}\d{1,3}$|^::1?$|^0{1,4}(:0{1,4}){0,7}$", parts[0]):
        line = parts[1]
    elif len(parts) >= 2:
        # Pi-hole-Exports haben manchmal Trailing-Kommentare ohne #
        line = parts[0]

    line = line.strip().strip(".").lower()

    # Regex-/Wildcard-Eintraege aussortieren - Technitium-Allow-Lists
    # erwarten reine Domains.
    if REGEXISH.search(line):
        return None
    if line.startswith("*"):
        return None
    if not DOMAIN_RE.match(line):
        return None
    return line


def main() -> int:
    urls = read_list_file(SOURCES)
    if not urls:
        print("sources.txt enthaelt keine URLs", file=sys.stderr)
        return 1

    collected: dict[str, set[str]] = {}
    dropped_total = 0
    failed: list[str] = []

    for url in urls:
        try:
            body = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN  {url}: {exc}", file=sys.stderr)
            failed.append(url)
            continue
        good, dropped = set(), 0
        for raw in body.splitlines():
            dom = normalize(raw)
            if dom:
                good.add(dom)
            elif raw.strip() and not raw.lstrip().startswith(("#", "!", "//", ";")):
                dropped += 1
        collected[url] = good
        dropped_total += dropped
        print(f"OK    {url}: {len(good)} Domains ({dropped} Zeilen verworfen)")

    if failed and len(failed) == len(urls):
        print("Alle Quellen fehlgeschlagen - allowlist.txt bleibt unveraendert.", file=sys.stderr)
        return 1

    merged: set[str] = set()
    for domains in collected.values():
        merged |= domains

    quarantined = {d for d in (normalize(x) for x in read_list_file(QUARANTINE)) if d}
    local = {d for d in (normalize(x) for x in read_list_file(LOCAL)) if d}

    removed = merged & quarantined
    final = sorted((merged - quarantined) | local)

    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = [
        "# DNS Allowlist (Technitium)",
        "#",
        "# AUTOGENERIERT von build.py - nicht von Hand bearbeiten.",
        "# Eigene Ausnahmen gehoeren in allowlist-local.txt.",
        "#",
        f"# Stand:      {stamp}",
        f"# Eintraege:  {len(final)}",
        f"# Quellen:    {len(collected)} von {len(urls)} erreichbar",
        f"# Quarantaene: {len(removed)} Eintraege entfernt (siehe quarantine.txt)",
        f"# Lokal:      {len(local)} eigene Eintraege",
        "#",
    ]
    for url in urls:
        n = len(collected.get(url, ()))
        mark = "ok " if url in collected else "ERR"
        header.append(f"# [{mark}] {n:>5}  {url}")
    header.append("")

    OUTPUT.write_text("\n".join(header + final) + "\n", encoding="utf-8")
    print(f"\n-> {OUTPUT.name}: {len(final)} Domains, {len(removed)} quarantaeniert")
    if failed:
        print(f"   {len(failed)} Quelle(n) nicht erreichbar - siehe Header.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
