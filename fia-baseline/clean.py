#!/usr/bin/env python3
"""Clean a folder of Notion CSV exports and check them for STRUCTURAL problems.

Relationship problems (unmatched names, "Untitled" links, one-sided relations, nodes without
edges) are NOT checked here; the loader reports those.

What it does:
  1. Normalizes whitespace and converts placeholder junk (N/A, TBD, -, ?, null...) into empty cells.
  2. Drops rows ONLY if they are missing a Name (invalid primary key).
  3. Drops entire COLUMNS that are completely empty or below --min-fill threshold.
  4. Fills the remaining empty cells with --fill (default NULL), but ONLY in plain property
     columns. Name, description, and relation columns are never filled (see notes below).
  5. Checks structure and reports it in cleanup_report.md (summary) and cleanup_issues.csv
     (every finding):
       - rows with no name (dropped)
       - duplicate names inside a file
       - rows with an empty description, or files with no description column
       - very short descriptions (--min-desc), which are often placeholders
       - the same description reused by different rows
       - duplicate column headers, or no recognised Name column
  6. Logs dropped columns, filled cells, and cleaning stats.

Why relation and description columns are not filled:
  - Relation columns: a filler word becomes a fake value that matches no node. It would count
    as an unmatched name and lower the match rate, which can stop the column from being
    detected as a relation at all. (Relation columns are only detected here so they can be
    protected; they are not checked.)
  - Description columns: a filler word would pass an empty-description check and get embedded,
    putting junk vectors into semantic search. Empty descriptions should be written or the
    row removed, not hidden.

The checks never change the cleaned files; they only report.

Usage:
  python clean.py notion_export/ --out cleaned/
  python clean.py notion_export/ --out cleaned/ --min-fill 0.05   # drop columns with < 5% filled cells
  python clean.py notion_export/ --out cleaned/ --fill ""         # do not fill anything
  python clean.py notion_export/ --out cleaned/ --min-desc 0      # skip the short-description check
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ---- helpers
NAME_COLS = ["Name", "Trait name"]
# DESC_CANDIDATES = column names that are likely to be descriptions; these columns are protected.
DESC_CANDIDATES = ["Description", "Definition", "Summary", "Intro", "Research Summary"]
URL_PAREN = re.compile(r"\s*\((?:https?://|notion://)[^)]*\)")
HASH_SUFFIX = re.compile(r"\s+(?=[0-9a-f]*\d)[0-9a-f]{8,}$", re.I)  # Notion id suffix: 8+ hex chars with a digit
QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
MIN_SHARED_DESC = 20  # shorter descriptions can legitimately repeat, so they are not flagged as duplicates


def clean(s):
    return " ".join(URL_PAREN.sub("", s or "").split())


def clean_header(h):
    return re.sub(r"^[^\w]+", "", h or "").strip()  # drops leading emoji/symbols


def entity_name(path):
    stem = re.sub(r"_all$", "", path.stem)
    return HASH_SUFFIX.sub("", stem).strip()


def norm_key(s):
    """Key used to compare names/descriptions: curly quotes straightened, case and spacing ignored."""
    return " ".join(clean(s).translate(QUOTES).casefold().split())


def parse_cell(cell, known):
    """Split a relation cell on commas, but re-join pieces that form a known name."""
    toks = [t.strip() for t in URL_PAREN.sub("", cell or "").split(",") if t.strip()]
    out, i = [], 0
    while i < len(toks):
        for j in range(min(len(toks), i + 8), i, -1):  # longest candidate first
            if norm_key(", ".join(toks[i:j])) in known:
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
    ap.add_argument(
        "--min-desc",
        type=int,
        default=15,
        help="flag descriptions shorter than this many characters (default 15; 0 disables)",
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
            raw_rows = list(reader)
        rows, cleared = [], 0
        for r in raw_rows:
            row = {}
            for c in cols:
                original = r.get(c) or ""
                v = norm(original)
                if original.strip() and not v:
                    cleared += 1  # a placeholder such as N/A or TBD was turned into an empty cell
                row[c] = v
            rows.append(row)
        if cols:
            data[out_name] = {
                "src": p.name,
                "cols": cols,
                "rows": rows,
                "cleared": cleared,
                "name_found": any(c in cols for c in NAME_COLS),
                "name_col": next((c for c in NAME_COLS if c in cols), cols[0]),
            }
    if not data:
        sys.exit(f"No CSV files found in {args.folder}")

    # ---- known names for relation discovery (used only to protect relation columns)
    known = set()
    for d in data.values():
        for r in d["rows"]:
            n = clean(r[d["name_col"]])
            if n:
                known.add(norm_key(n))

    issues = []  # (issue, file, line_in_original, value, detail)
    summary, dropped_cols_report = {}, defaultdict(list)
    no_desc = {}
    kept = {}

    for fname, d in data.items():
        cols, rows, nc = d["cols"], d["rows"], d["name_col"]
        label = fname[:-4]

        # Protect primary name, description candidates, and relation columns
        rel_cols = []
        for c in cols:
            if c == nc:
                continue
            toks = [t for r in rows for t in parse_cell(r[c], known)]
            if toks and sum(norm_key(t) in known for t in toks) / len(toks) >= 0.1:
                rel_cols.append(c)
        desc_cols = [c for c in cols if clean_header(c) in DESC_CANDIDATES]
        protected_cols = {nc, *rel_cols, *desc_cols}

        # ---- structural checks (on the normalized data, before any column is dropped)
        dup_headers = [h for h, n in Counter(cols).items() if n > 1]
        if dup_headers:
            issues.append(("duplicate_header", label, "", ", ".join(dup_headers),
                           "duplicate column titles: only the last column's values are kept"))
        if not d["name_found"]:
            issues.append(("no_name_column", label, "", nc,
                           f"no column named {' or '.join(NAME_COLS)}; the first column '{clean_header(nc)}' was used as the name"))
        if not rows:
            issues.append(("empty_file", label, "", "", "file has a header but no rows"))

        valid = [(i + 2, r) for i, r in enumerate(rows) if r[nc]]  # (line in the original file, row)
        for i, r in enumerate(rows):
            if not r[nc]:
                issues.append(("no_name", label, i + 2, "", "row has no name; dropped"))

        by_name = defaultdict(list)
        for line, r in valid:
            by_name[norm_key(r[nc])].append((line, r[nc]))
        for items in by_name.values():
            if len(items) > 1:
                issues.append(("duplicate_name", label, items[0][0], items[0][1],
                               f"{len(items)} rows share this name (lines {', '.join(str(l) for l, _ in items)}); "
                               f"a loader keeps only one"))

        missing = 0
        by_desc = defaultdict(list)
        for line, r in valid:
            desc = next((r[c] for c in desc_cols if r[c]), "")
            if not desc:
                missing += 1
                issues.append(("empty_description", label, line, r[nc],
                               "description is empty" if desc_cols else "no description column in this file"))
                continue
            if args.min_desc and len(desc) < args.min_desc:
                issues.append(("short_description", label, line, r[nc], f"{len(desc)} characters: '{desc}'"))
            if len(desc) >= MIN_SHARED_DESC:
                by_desc[norm_key(desc)].append((line, r[nc]))
        for items in by_desc.values():
            names = [n for _, n in items]
            if len(set(norm_key(n) for n in names)) > 1:
                issues.append(("duplicate_description", label, items[0][0], names[0],
                               f"same description on {len(names)} rows: " + "; ".join(names[:5])
                               + (" ..." if len(names) > 5 else "")))
        no_desc[fname] = (missing, len(valid), bool(desc_cols))

        # Remove ONLY rows with no name
        valid_rows = [r for _, r in valid]

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

        kept[fname] = (kept_cols, out_rows)
        summary[fname] = {
            "in_rows": len(rows),
            "out_rows": len(out_rows),
            "in_cols": len(cols),
            "out_cols": len(kept_cols),
            "dropped_cols": dropped_cols,
            "filled": sum(fill_counts.values()),
            "cleared": d["cleared"],
        }

    # ---- write outputs
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for fname, (cols, out_rows) in kept.items():
        with open(out / fname, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(out_rows)

    with open(out / "cleanup_issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["issue", "file", "line_in_original", "value", "detail"])
        w.writerows(issues)

    by_issue = defaultdict(list)
    for it in issues:
        by_issue[it[0]].append(it)

    # ---- write markdown report
    L = [
        "# Column Cleanup Report\n",
        f"Settings: min-fill threshold = {args.min_fill:.1%} (columns with less data were dropped); "
        f"empty property cells filled with '{args.fill}'.\n",
        "| File | Rows In | Rows Out | Total Cols | Kept Cols | Dropped Cols | Cells Filled | Placeholders Cleared |\n|---|---|---|---|---|---|---|---|",
    ]
    for fname, s in summary.items():
        L.append(
            f"| {fname} | {s['in_rows']} | {s['out_rows']} | {s['in_cols']} | {s['out_cols']} | {len(s['dropped_cols'])} | {s['filled']} | {s['cleared']} |"
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

    L.append("\n# Structural checks\n")
    L.append("Every individual finding is in `cleanup_issues.csv`. Relationship checks are done by the loader.\n")
    L.append("| Check | Findings | What it means |\n|---|---|---|")
    meanings = [
        ("no_name", "Rows with no name", "dropped from the cleaned file"),
        ("duplicate_name", "Duplicate names", "rows with the same name merge into one node"),
        ("empty_description", "Empty descriptions", "left blank on purpose; write one or remove the row"),
        ("short_description", "Very short descriptions", "often placeholders; semantic search is weak on them"),
        ("duplicate_description", "Reused descriptions", "different rows share identical text; check for copy-paste"),
        ("duplicate_header", "Duplicate column titles", "values of the earlier column are lost"),
        ("no_name_column", "Files with no Name column", "the first column was used as the name"),
        ("empty_file", "Files with no rows", "nothing to load"),
    ]
    for key, title, meaning in meanings:
        L.append(f"| {title} | {len(by_issue[key])} | {meaning} |")

    L.append("\n## Empty descriptions by file\n")
    L.append("| File | Rows without a description | Of | Note |\n|---|---|---|---|")
    anyd = False
    for fname, (n, total, has_col) in no_desc.items():
        if n:
            anyd = True
            L.append(f"| {fname[:-4]} | {n} | {total} | {'' if has_col else 'no description column in this file'} |")
    if not anyd:
        L.append("| (none) | | | |")

    for key, title in [("duplicate_name", "Duplicate names"), ("no_name", "Rows with no name (dropped)"),
                       ("short_description", "Very short descriptions"), ("duplicate_description", "Reused descriptions"),
                       ("duplicate_header", "Duplicate column titles"), ("no_name_column", "Files with no Name column"),
                       ("empty_file", "Files with no rows")]:
        items = by_issue[key]
        if not items:
            continue
        L.append(f"\n## {title}\n")
        for it in items[:10]:
            where = f" line {it[2]}" if it[2] != "" else ""
            val = f" '{it[3]}'" if it[3] else ""
            L.append(f"- {it[1]}{where}:{val} {it[4]}")
        if len(items) > 10:
            L.append(f"- ...and {len(items) - 10} more in cleanup_issues.csv")

    (out / "cleanup_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    tot_cols_in = sum(s["in_cols"] for s in summary.values())
    tot_cols_out = sum(s["out_cols"] for s in summary.values())
    tot_filled = sum(s["filled"] for s in summary.values())
    print(
        f"Finished cleaning {len(summary)} files: {tot_cols_in} total columns -> {tot_cols_out} kept "
        f"({tot_cols_in - tot_cols_out} empty/sparse columns dropped), {tot_filled} empty cells filled with '{args.fill}'."
    )
    print(f"Wrote cleaned CSV files, cleanup_report.md and cleanup_issues.csv to {out}/")
    print("Saved files:")
    for fname, d in data.items():
        print(f"  {d['src']}  ->  {fname}")
    for src, out_name in skipped:
        print(f"  {src}  ->  (skipped: same name as {out_name})")
    print("Structural findings:")
    for key, title, _ in meanings:
        print(f"  {len(by_issue[key]):>6}  {title.lower()}")
    print("See cleanup_report.md for the summary.")


if __name__ == "__main__":
    main()