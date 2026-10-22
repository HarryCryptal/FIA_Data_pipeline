#!/usr/bin/env python3
"""Import cleaned Notion CSVs into the `nodes` table (embeddings + upsert).

Usage:
  python import.py                      # reads ./cleaned
  python import.py --dir cleaned --dry-run   # validate only, no model load, no DB writes

Design notes:
  - Reads every cell as a string (no pandas NA guessing), so values like "None"/"NA" are never lost.
  - Cleans emoji-prefixed headers the same way clean.py / visualize.py do.
  - Coalesces description candidates per row (first non-empty wins).
  - Batch-encodes embeddings and batch-inserts with execute_values.
  - One transaction per file: a failure rolls back that file only and is reported loudly.
"""

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json, execute_values

load_dotenv()

DB_PARAMS = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": os.getenv("POSTGRES_PORT", "5433"),
    "dbname": os.getenv("POSTGRES_DB", "fia"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# Cleaned CSV stem -> nodes.type (must match the CHECK constraint in schema.sql)
NODE_TYPES = {
    "Player typologies": "player_type",
    "Universal Neurological Encoding system": "red_flag",  # adjust based on UNES decision
    "Abuse Techniques": "abuse_technique",
    "Vulnerability Traits": "vulnerability_trait",
    "Trauma": "trauma_pathway",
    "Mental processes": "mental_process",
    "Media characters": "media_character",
}

# Keep in sync with DESC_CANDIDATES in clean.py (clean.py must protect every column listed here,
# otherwise sparse description columns can be dropped before they reach this script).
NAME_CANDIDATES = ["Name", "Trait name"]
DESC_CANDIDATES = ["Description", "Definition", "Summary", "Research Summary", "Intro"]

URL_PAREN = re.compile(r"\s*\((?:https?://|notion://)[^)]*\)")
EMPTY = {"", "null", "nan"}  # "NULL" is what clean.py's default --fill writes
EMBED_BATCH = 64


def clean_header(h):
    return re.sub(r"^[^\w]+", "", h or "").strip()


def cell(v):
    v = " ".join(URL_PAREN.sub("", v or "").split())
    return "" if v.casefold() in EMPTY else v


def load_file(path):
    """Return (records, stats). records: list of (name, description, metadata)."""
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return [], Counter(empty_file=1)
    df.columns = [clean_header(c) for c in df.columns]
    cols = list(df.columns)

    name_col = next((c for c in NAME_CANDIDATES if c in cols), cols[0])
    desc_cols = [c for c in DESC_CANDIDATES if c in cols]
    stats = Counter()
    if not desc_cols:
        stats["no_description_column"] = len(df)
        return [], stats

    records = {}
    reserved = {name_col, *desc_cols}
    for row in df.to_dict("records"):
        name = cell(row[name_col])
        if not name:
            stats["no_name"] += 1
            continue
        desc = next((d for d in (cell(row[c]) for c in desc_cols) if d), "")
        if not desc:
            stats["no_description"] += 1
            continue
        meta = {k: cell(v) for k, v in row.items() if k not in reserved and cell(v)}
        if name in records:
            stats["duplicate_name"] += 1  # last row wins
        records[name] = (name, desc, meta)
    return list(records.values()), stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="cleaned", help="folder with cleaned CSVs (default: cleaned)")
    ap.add_argument("--dry-run", action="store_true", help="validate files only; no model, no DB")
    args = ap.parse_args()

    type_by_stem = {k.casefold(): v for k, v in NODE_TYPES.items()}
    files = sorted(Path(args.dir).glob("*.csv"))
    if not files:
        sys.exit(f"No CSV files found in {args.dir}/")

    plan, seen_stems = [], set()
    for path in files:
        stem = path.stem.strip().casefold()
        node_type = type_by_stem.get(stem)
        if node_type is None:
            print(f"Skipping {path.name}: not mapped to a node type.")
            continue
        seen_stems.add(stem)
        records, stats = load_file(path)
        skipped = ", ".join(f"{k}={v}" for k, v in stats.items())
        print(f"{path.name}: {len(records)} importable" + (f" | skipped: {skipped}" if skipped else ""))
        plan.append((path.name, node_type, records))

    for stem, t in type_by_stem.items():
        if stem not in seen_stems:
            print(f"Warning: no CSV found for mapped type '{t}' ({stem}).")

    if args.dry_run:
        return

    from sentence_transformers import SentenceTransformer

    print("Loading all-MiniLM-L6-v2 (384-dim)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    conn = psycopg2.connect(**DB_PARAMS)
    register_vector(conn)
    failed = []

    sql = """
        INSERT INTO nodes (type, name, description, embedding, metadata)
        VALUES %s
        ON CONFLICT (type, name) DO UPDATE
        SET description = EXCLUDED.description,
            embedding   = EXCLUDED.embedding,
            metadata    = EXCLUDED.metadata
    """

    for fname, node_type, records in plan:
        if not records:
            continue
        texts = [f"{name}. {desc}" for name, desc, _ in records]

        # MiniLM silently truncates past max_seq_length tokens; flag it.
        lengths = [len(ids) for ids in model.tokenizer(texts, truncation=False)["input_ids"]]
        long_rows = [records[i][0] for i, n in enumerate(lengths) if n > model.max_seq_length]
        if long_rows:
            print(f"  {fname}: {len(long_rows)} rows exceed {model.max_seq_length} tokens and will be truncated "
                  f"for embedding (e.g. {long_rows[:3]}).")

        vecs = model.encode(texts, batch_size=EMBED_BATCH, normalize_embeddings=True, show_progress_bar=True)
        rows = [
            (node_type, name, desc, vec, Json(meta))
            for (name, desc, meta), vec in zip(records, vecs)
        ]
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, rows, page_size=200)
            conn.commit()
            print(f"  {fname}: upserted {len(rows)} {node_type} nodes.")
        except Exception as e:
            conn.rollback()
            failed.append(fname)
            print(f"  {fname}: FAILED, rolled back this file: {e}")

    conn.close()
    if failed:
        sys.exit(f"Import finished with failures: {failed}")
    print("Node import complete.")


if __name__ == "__main__":
    main()