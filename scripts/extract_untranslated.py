#!/usr/bin/env python3
"""
Extract entries from main.pot that are missing or untranslated in ar.po.
Outputs a .pot file with only those entries (empty msgstr) for you to translate.

Usage:
  python scripts/extract_untranslated.py [--pot PATH] [--po PATH] [-o OUTPUT]
  Default: frappe v16 locale paths, output: to_translate.pot in same dir as ar.po.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _decode_po_string(s: str) -> str:
    """Unescape and join PO string (handles \\n, \\t, \\", etc.)."""
    if not s:
        return ""
    # PO: "line1\\n" "line2" -> line1\nline2; unescape backslash sequences
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "n":
                out.append("\n")
            elif n == "t":
                out.append("\t")
            elif n == "r":
                out.append("\r")
            elif n == '"':
                out.append('"')
            elif n == "\\":
                out.append("\\")
            else:
                out.append(s[i : i + 2])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _parse_po_string_value(line: str) -> str | None:
    """Extract quoted string value from a line like: msgid \"...\" or \"...\" """
    m = re.match(r'^\s*"(.*)"\s*$', line)
    if not m:
        return None
    return _decode_po_string(m.group(1))


def _read_entry_lines(f) -> list[str] | None:
    """Read one PO entry (until blank line or EOF). Returns list of lines or None at EOF."""
    lines: list[str] = []
    while True:
        line = f.readline()
        if not line:
            return lines if lines else None
        line = line.rstrip("\n\r")
        if line.strip() == "":
            return lines if lines else None
        lines.append(line)


def _get_msgid_from_block(lines: list[str]) -> str:
    """Extract full msgid value from an entry block (handles multiline)."""
    value_parts: list[str] = []
    in_msgid = False
    for raw in lines:
        if raw.startswith("msgid "):
            in_msgid = True
            rest = raw[6:].strip()
            if rest and rest.startswith('"'):
                v = _parse_po_string_value(rest)
                if v is not None:
                    value_parts.append(v)
            continue
        if raw.startswith("msgstr") or raw.startswith("msgid_plural") or raw.startswith("msgctxt "):
            in_msgid = False
        if in_msgid and raw.strip().startswith('"'):
            v = _parse_po_string_value(raw.strip())
            if v is not None:
                value_parts.append(v)
    return "".join(value_parts)


def _get_msgstr_from_block(lines: list[str]) -> str:
    """Extract first msgstr value from an entry block (msgstr or msgstr[0])."""
    value_parts: list[str] = []
    in_msgstr = False
    for raw in lines:
        if re.match(r"^\s*msgstr\b", raw):
            in_msgstr = True
            rest = raw.split("msgstr", 1)[1].strip()
            if rest and rest.startswith('"'):
                v = _parse_po_string_value(rest)
                if v is not None:
                    value_parts.append(v)
            continue
        if re.match(r"^\s*msgstr\[", raw):
            rest = re.sub(r"^\s*msgstr\[\d+\]\s*", "", raw).strip()
            if rest.startswith('"'):
                v = _parse_po_string_value(rest)
                if v is not None:
                    value_parts.append(v)
            in_msgstr = True
            continue
        if raw.strip().startswith("msgid ") or raw.strip().startswith("msgctxt "):
            in_msgstr = False
        if in_msgstr and raw.strip().startswith('"'):
            v = _parse_po_string_value(raw.strip())
            if v is not None:
                value_parts.append(v)
    return "".join(value_parts)


def collect_translated_msgids(po_path: Path) -> set[str]:
    """Stream ar.po and return set of msgids that have a non-empty msgstr."""
    translated: set[str] = set()
    with open(po_path, "r", encoding="utf-8", errors="replace") as f:
        while True:
            lines = _read_entry_lines(f)
            if lines is None:
                break
            msgid = _get_msgid_from_block(lines)
            # Skip header (empty msgid)
            if msgid == "":
                continue
            msgstr = _get_msgstr_from_block(lines)
            if msgstr.strip():
                translated.add(msgid)
    return translated


def emit_untranslated_from_pot(
    pot_path: Path,
    translated_msgids: set[str],
    out_path: Path,
    *,
    header_lines: list[str] | None = None,
) -> int:
    """Stream main.pot and write entries whose msgid is not in translated_msgids. Returns count."""
    count = 0
    header_written = False

    with open(pot_path, "r", encoding="utf-8", errors="replace") as fin:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fout:
            while True:
                lines = _read_entry_lines(fin)
                if lines is None:
                    break
                msgid = _get_msgid_from_block(lines)
                if msgid == "":
                    # Write header once
                    if header_lines is not None:
                        fout.write("\n".join(header_lines) + "\n\n")
                    else:
                        fout.write("\n".join(lines) + "\n\n")
                    header_written = True
                    continue
                if msgid in translated_msgids:
                    continue
                # Write entry with empty msgstr (ensure msgstr "" for single, msgstr[0] "" etc for plural)
                out_lines = _rewrite_entry_empty_msgstr(lines)
                fout.write("\n".join(out_lines) + "\n\n")
                count += 1
    return count


def _rewrite_entry_empty_msgstr(lines: list[str]) -> list[str]:
    """Replace msgstr (and msgstr[n]) values with empty string in an entry block."""
    result: list[str] = []
    in_msgstr = False
    for raw in lines:
        if re.match(r"^\s*msgstr\s+", raw):
            result.append(re.sub(r'msgstr\s+".*"', 'msgstr ""', raw, count=1))
            in_msgstr = True
            continue
        m = re.match(r"^(\s*msgstr\[\d+\]\s+)\".*\"", raw)
        if m:
            result.append(m.group(1) + '""')
            in_msgstr = True
            continue
        if raw.strip().startswith("msgid ") or raw.strip().startswith("msgctxt "):
            in_msgstr = False
        if in_msgstr and raw.strip().startswith('"') and raw.strip() != '""':
            result.append('""')
            continue
        result.append(raw)
    return result


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    default_pot = base / "arabic_translations/locale/other-apps/v16/frappe/frappe/locale/main.pot"
    default_po = base / "arabic_translations/locale/other-apps/v16/frappe/frappe/locale/ar.po"

    ap = argparse.ArgumentParser(description="Extract untranslated entries from .pot vs .po")
    ap.add_argument("--pot", type=Path, default=default_pot, help="Template file (main.pot)")
    ap.add_argument("--po", type=Path, default=default_po, help="Translation file (ar.po)")
    ap.add_argument("-o", "--output", type=Path, default=None, help="Output .pot (default: same dir as ar.po, to_translate.pot)")
    args = ap.parse_args()

    pot_path = args.pot
    po_path = args.po
    out_path = args.output or (po_path.parent / "to_translate.pot")

    if not po_path.is_file():
        print(f"Error: {po_path} not found", file=sys.stderr)
        return 1
    if not pot_path.is_file():
        print(f"Error: {pot_path} not found", file=sys.stderr)
        return 1

    print("Collecting translated msgids from", po_path, "...", flush=True)
    translated = collect_translated_msgids(po_path)
    print(f"  Found {len(translated)} translated entries.", flush=True)

    print("Writing untranslated entries from", pot_path, "to", out_path, "...", flush=True)
    # Use a minimal header for the output
    header = [
        '# Extracted untranslated entries for manual translation.',
        '# Source template: ' + str(pot_path),
        '# Translations from: ' + str(po_path),
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
    ]
    n = emit_untranslated_from_pot(pot_path, translated, out_path, header_lines=header)
    print(f"  Wrote {n} entries to {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
