#!/usr/bin/env python3
"""Clean a folder of Notion CSV exports by dropping completely empty or under-filled COLUMNS.

What it does:
  1. Normalizes whitespace and converts placeholder junk (N/A, TBD, -, ?, null...) into empty cells.
  2. Drops rows ONLY if they are missing a Name (invalid primary key).
  3. Identifies and drops entire COLUMNS that are completely empty or below --min-fill threshold.
  4. Fills the remaining empty cells with --fill (default NULL), but ONLY in plain property
     columns. Name, description, and relation columns are never filled (see notes below).
  5. Logs dropped columns, filled cells, and cleaning stats to cleanup_report.md.

Why relation and description columns are not filled:
  - Relation columns: a filler word becomes a fake value that matches no node. convert.py would
    count it as an unmatched name and the match rate drops, which can stop the column from being
    detected as a relation at all.
  - Description columns: a filler word would pass import.py's empty-description check and get
    embedded, putting junk vectors into semantic search. Empty descriptions should be written or
    the row removed, not hidden.

Usage:
  python clean.py notion_export/ --out cleaned/
  python clean.py notion_export/ --out cleaned/ --min-fill 0.05   # drop columns with < 5% filled cells
  python clean.py notion_export/ --out cleaned/ --fill ""         # do not fill anything
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ---- helpers
# DESC_CANDIDATES = protected column names that are likely to be descriptions and will be protected. 
DESC_CANDIDATES = ["Description", "Research Summary", "Summary"]
URL_PAREN = re.compile(r"\s*\((?:https?://|notion://)[^)]*\)")
HASH_SUFFIX = re.compile(r"\s+(?=[0-9a-f]*\d)[0-9a-f]{8,}$", re.I)  # Notion id suffix: 8+ hex chars with a digit


def clean(s):
    return " ".join(URL_PAREN.sub("", s or "").split())


def clean_header(h):
    return re.sub(r"^[^\w]+", "", h or "").strip()  # drops leading emoji/symbols


def entity_name(path):
    stem = re.sub(r"_all$", "", path.stem)
    return HASH_SUFFIX.sub("", stem).strip()


def parse_cell(cell, known):
    """Split a relation cell on commas, but re-join pieces that form a known name."""
    toks = [t.strip() for t in URL_PAREN.sub("", cell or "").split(",") if t.strip()]
    out, i = [], 0
    while i < len(toks):
        for j in range(len(toks), i, -1):  # longest candidate first
            if ", ".join(toks[i:j]).casefold() in known:
                out.append(", ".join(toks[i:j]))
                i = j
                break
        else:
            out.append(toks[i])
            i += 1
    return out


PLACEHOLDERS = {
    "n/a",
    "na",
    "#n/a",
    "null",
    "nil",
    "-",
    "--",
    "\u2014",
    "tbd",
    "?",
}


def norm(v):
    v = " ".join((v or "").replace("\u00a0", " ").split())
    return "" if v.casefold() in PLACEHOLDERS else v


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("folder", help="folder with the raw Notion CSV exports")
    ap.add_argument("--out", default="cleaned", help="output folder (default: cleaned)")
    ap.add_argument(
        "--min-fill",
        type=float,
        default=0.01,
        help="drop columns if less than this share of rows have data (default 0.01 = 1%% fill; 0.0 means drop only 100%% empty columns)",
    )
    ap.add_argument(
        "--fill",
        default="NULL",
        help="text written into empty cells of plain property columns (default: NULL; use '' to disable)",
    )
    args = ap.parse_args()

    # ---- load + normalize
    # Saved file names drop Notion's trailing id and "_all". If two exports reduce to the same name
    # (the full "_all" database and a filtered view), keep the "_all" one and say so in the report.
    groups = defaultdict(list)
    for p in sorted(Path(args.folder).glob("*.csv")):
        groups[(entity_name(p) or p.stem) + ".csv"].append(p)
    chosen, skipped = {}, []
    for out_name, ps in groups.items():
        ps = sorted(ps, key=lambda p: (not p.stem.endswith("_all"), p.name))
        chosen[out_name] = ps[0]
        skipped.extend((p.name, out_name) for p in ps[1:])

    data = {}
    for out_name, p in chosen.items():
        with open(p, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            rows = [{c: norm(r.get(c, "")) for c in cols} for r in reader]
        if cols:
            data[out_name] = {
                "src": p.name,
                "ent": entity_name(p),
                "cols": cols,
                "rows": rows,
                "name_col": "Name" if "Name" in cols else cols[0],
            }
    if not data:
        sys.exit(f"No CSV files found in {args.folder}")

    # ---- known names for relation discovery
    known = set()
    for d in data.values():
        for r in d["rows"]:
            n = clean(r[d["name_col"]])
            if n:
                known.add(n.casefold())

    summary, dropped_cols_report, blank_desc = {}, defaultdict(list), defaultdict(list)
    kept = {}

    for fname, d in data.items():
        cols, rows, nc = d["cols"], d["rows"], d["name_col"]

        # Protect primary name, description candidates, and relation columns
        rel_cols = []
        for c in cols:
            if c == nc:
                continue
            toks = [t for r in rows for t in parse_cell(r[c], known)]
            if toks and sum(t.casefold() in known for t in toks) / len(toks) >= 0.1:
                rel_cols.append(c)
        desc_cols = [c for c in cols if clean_header(c) in DESC_CANDIDATES]
        protected_cols = {nc, *rel_cols, *desc_cols}

        # Remove ONLY rows with no name
        valid_rows = [r for r in rows if r[nc]]

        # Evaluate columns for retention
        kept_cols = []
        dropped_cols = []
        total_valid_rows = len(valid_rows) if valid_rows else 1

        for c in cols:
            filled_count = sum(1 for r in valid_rows if r[c])
            fill_rate = filled_count / total_valid_rows

            if c in protected_cols or fill_rate >= args.min_fill:
                kept_cols.append(c)
            else:
                dropped_cols.append((clean_header(c), filled_count, fill_rate))
                dropped_cols_report[fname].append(
                    f"'{clean_header(c)}' ({filled_count}/{total_valid_rows} filled)"
                )

        # Build output rows: keep only kept columns, fill empties in plain property columns
        fill_counts = Counter()
        out_rows = []
        for r in valid_rows:
            row = {}
            for c in kept_cols:
                v = r[c]
                if not v and args.fill and c not in protected_cols:
                    v = args.fill
                    fill_counts[clean_header(c)] += 1
                row[c] = v
            out_rows.append(row)
            if desc_cols and not any(r[c] for c in desc_cols):
                blank_desc[fname].append(r[nc])

        kept[fname] = (kept_cols, out_rows)
        summary[fname] = {
            "in_rows": len(rows),
            "out_rows": len(out_rows),
            "in_cols": len(cols),
            "out_cols": len(kept_cols),
            "dropped_cols": dropped_cols,
            "filled": sum(fill_counts.values()),
        }

    # ---- write outputs
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for fname, (cols, out_rows) in kept.items():
        with open(out / fname, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(out_rows)

    # ---- write markdown report
    L = [
        "# Column Cleanup Report\n",
        f"Settings: min-fill threshold = {args.min_fill:.1%} (columns with less data were dropped); "
        f"empty property cells filled with '{args.fill}'.\n",
        "| File | Rows In | Rows Out | Total Cols | Kept Cols | Dropped Cols | Cells Filled |\n|---|---|---|---|---|---|---|",
    ]
    for fname, s in summary.items():
        L.append(
            f"| {fname} | {s['in_rows']} | {s['out_rows']} | {s['in_cols']} | {s['out_cols']} | {len(s['dropped_cols'])} | {s['filled']} |"
        )

    L.append("\n## Files written\n\n| Original file | Saved as |\n|---|---|")
    for fname, d in data.items():
        L.append(f"| {d['src']} | {fname} |")
    for src, out_name in skipped:
        L.append(f"| {src} | (not written: same name as {out_name}; the _all export was used) |")

    if dropped_cols_report:
        L.append("\n## Dropped Columns Detail\n")
        for fname, cols_list in dropped_cols_report.items():
            L.append(f"**{fname}**:")
            L.extend(f"- {col_info}" for col_info in cols_list)
            L.append("")

    if blank_desc:
        L.append("\n## Rows with an empty description (left blank on purpose)\n")
        L.append("import.py rejects empty descriptions. Write a real description or remove the row.\n")
        for fname, names in blank_desc.items():
            L.extend(f"- {fname}: '{n}'" for n in names)

    (out / "cleanup_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    tot_cols_in = sum(s["in_cols"] for s in summary.values())
    tot_cols_out = sum(s["out_cols"] for s in summary.values())
    tot_filled = sum(s["filled"] for s in summary.values())
    print(
        f"Finished cleaning {len(summary)} files: {tot_cols_in} total columns -> {tot_cols_out} kept "
        f"({tot_cols_in - tot_cols_out} empty/sparse columns dropped), {tot_filled} empty cells filled with '{args.fill}'."
    )
    print(f"Wrote cleaned CSV files and cleanup_report.md to {out}/")
    print("Saved files:")
    for fname, d in data.items():
        print(f"  {d['src']}  ->  {fname}")
    for src, out_name in skipped:
        print(f"  {src}  ->  (skipped: same name as {out_name})")
    if blank_desc:
        print("Some rows have empty descriptions: see cleanup_report.md.")


if __name__ == "__main__":
    main()