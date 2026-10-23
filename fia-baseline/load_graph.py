#!/usr/bin/env python3
"""Load the cleaned CSVs into Postgres + pgvector as a graph, then show multi-hop paths.

  python load_graph.py                 # rebuild nodes + edges from ./cleaned and print a report
  python load_graph.py --dry-run       # parse + match names only (no model, no DB writes)
  python load_graph.py --hops "Mr. Always Right" --depth 2 --to vulnerability_trait
  python load_graph.py --search "love bombing"

Every load is a full rebuild in ONE transaction (TRUNCATE + insert). If anything fails, the
database is left exactly as it was. Run schema.sql once first (tables + pgvector extension).
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
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

# ---------------------------------------------------------------- configuration
# CSV file name (underscores/case ignored) -> nodes.type
FILES = {
    "player typologies": "player_type",
    "red flags": "red_flag",
    "abuse techniques": "abuse_technique",
    "vulnerability traits": "vulnerability_trait",
    "trauma": "trauma_pathway",
    "mental processes": "mental_process",
    "media characters": "media_character",
    "universal neurological encoding system": "unes_trait",
}
NODE_TYPES = sorted(set(FILES.values()) | {"flavor_of_abuse"})

# (this file's type, column in that file, type of the node named in the cell, rel_type, direction)
#   direction "out": this row -> named node      "in": named node -> this row
# Columns that exist on both sides of a Notion relation are listed on both; duplicates collapse.
RELATIONS = [
    ("player_type", "He might use these techniques", "abuse_technique", "USES", "out"),
    ("player_type", "Vulnerability Traits", "vulnerability_trait", "TARGETS", "out"),
    ("player_type", "Red flags", "red_flag", "HAS_RED_FLAG", "out"),
    ("player_type", "Media characters", "media_character", "EXEMPLIFIES", "in"),
    ("red_flag", "Player typologies", "player_type", "HAS_RED_FLAG", "in"),
    ("red_flag", "UNES Traits", "unes_trait", "ACCOMPANIES", "out"),
    ("vulnerability_trait", "Player typologies", "player_type", "TARGETS", "in"),
    ("vulnerability_trait", "Abuse Techniques", "abuse_technique", "EXPLOITS", "in"),
    ("media_character", "Player typologies", "player_type", "EXEMPLIFIES", "out"),
    ("mental_process", "Vulnerability Traits", "vulnerability_trait", "EXPLOITS", "out"),
    ("mental_process", "Abuse Techniques", "abuse_technique", "OPERATES_IN", "in"),
    ("trauma_pathway", "Player typologies", "player_type", "PRODUCES", "in"),
    ("trauma_pathway", "Abuse Techniques", "abuse_technique", "PRODUCES", "in"),
    ("unes_trait", "Abuse Techniques", "abuse_technique", "ACCOMPANIES", "in"),
    ("abuse_technique", "UNES connection", "unes_trait", "ACCOMPANIES", "out"),
]

NAME_COLS = ["Name", "Trait name"]
DESC_COLS = ["Description", "Definition", "Summary", "Intro", "Research Summary"]
IGNORE = {"Cleanup note", "Cleanup flag", "Updated?", "Main FIA Type?", "Data Links"}  # working notes
NO_DESC = IGNORE | {"FIA ID", "link to DOI", "Research papers", "Research"}  # never composed into a description

URL_PAREN = re.compile(r"\s*\((?:https?://|notion://)[^)]*\)")
EMPTY = {"", "null", "nan"}  # "NULL" is what clean.py's default --fill writes
QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
LOW_MATCH = 0.8


# ---------------------------------------------------------------- helpers
def clean_header(h):
    return re.sub(r"^[^\w]+", "", h or "").strip()


def cell(v):
    v = " ".join(URL_PAREN.sub("", v or "").split())
    return "" if v.casefold() in EMPTY else v


def norm(s):
    return " ".join(s.translate(QUOTES).casefold().split())


def split_cell(text, known):
    """Split on commas, but re-join pieces that together form a known name ("Gaslighting: A, B")."""
    toks = [t.strip() for t in text.split(",") if t.strip()]
    out, i = [], 0
    while i < len(toks):
        for j in range(min(len(toks), i + 6), i, -1):
            cand = ", ".join(toks[i:j])
            if norm(cand) in known:
                out.append((cand, True))
                i = j
                break
        else:
            out.append((toks[i], False))
            i += 1
    return out


# ---------------------------------------------------------------- parse CSVs
def read_tables(folder):
    files = sorted(Path(folder).glob("*.csv"))
    if not files:
        sys.exit(f"No CSV files found in {folder}/")
    tables = {}
    for path in files:
        node_type = FILES.get(path.stem.replace("_", " ").strip().casefold())
        if node_type is None:
            print(f"Skipping {path.name}: not in FILES.")
            continue
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except pd.errors.EmptyDataError:
            print(f"Skipping {path.name}: empty file.")
            continue
        df.columns = [clean_header(c) for c in df.columns]
        cols = list(df.columns)
        tables[node_type] = {
            "cols": cols,
            "rows": df.to_dict("records"),
            "name_col": next((c for c in NAME_COLS if c in cols), cols[0]),
        }
    for t in sorted(set(FILES.values()) - set(tables)):
        print(f"Warning: no CSV found for {t}.")
    return tables


def build_nodes(tables):
    """Every named row becomes a node. Rows without a real description get one composed from
    their own text fields (flagged in metadata), so no node is lost and none is empty."""
    rel_cols = defaultdict(set)
    for src_type, col, *_ in RELATIONS:
        rel_cols[src_type].add(col)

    nodes, stats = {}, defaultdict(Counter)
    for t, tab in tables.items():
        cols, nc = tab["cols"], tab["name_col"]
        desc_cols = [c for c in DESC_COLS if c in cols]
        text_cols = [c for c in cols if c not in {nc, *desc_cols, *rel_cols[t], *NO_DESC}]
        for r in tab["rows"]:
            name = cell(r[nc])
            if not name:
                stats[t]["no_name"] += 1
                continue
            desc = next((d for d in (cell(r[c]) for c in desc_cols) if d), "")
            synthesized = not desc
            if synthesized:
                parts = [f"{c}: {cell(r[c])}" for c in text_cols if cell(r[c])]
                desc = f"{name}. " + "; ".join(parts) if parts else name
                stats[t]["composed_description"] += 1
            meta = {c: cell(r[c]) for c in cols if c not in {nc, *desc_cols, *IGNORE} and cell(r[c])}
            if synthesized:
                meta["description_synthesized"] = True
            key = (t, norm(name))
            if key in nodes:
                stats[t]["duplicate_name"] += 1  # last row wins
            nodes[key] = {
                "type": t,
                "name": name,
                "desc": desc,
                "text": desc if synthesized else f"{name}. {desc}",  # text that gets embedded
                "meta": meta,
            }
            stats[t]["nodes"] += 1
    return nodes, stats


def build_edges(tables, nodes):
    known = defaultdict(set)
    for t, n in nodes:
        known[t].add(n)

    edges, col_stats, unmatched = set(), {}, defaultdict(Counter)
    for src_type, col, dst_type, rel, direction in RELATIONS:
        tab = tables.get(src_type)
        if tab is None:
            continue
        if col not in tab["cols"]:
            print(f"Warning: column '{col}' not found for {src_type}.")
            continue
        total = matched = 0
        for r in tab["rows"]:
            name = cell(r[tab["name_col"]])
            if not name:
                continue
            for tok, ok in split_cell(cell(r[col]), known[dst_type]):
                total += 1
                if not ok:
                    unmatched[(src_type, col)][tok] += 1
                    continue
                matched += 1
                a, b = (src_type, norm(name)), (dst_type, norm(tok))
                if a == b:
                    continue
                edges.add((a, b, rel) if direction == "out" else (b, a, rel))
        col_stats[(src_type, col, rel)] = (matched, total)
    return edges, col_stats, unmatched


def print_parse_report(stats, col_stats, unmatched, edges):
    print("\nNodes")
    for t, s in sorted(stats.items()):
        extra = ", ".join(f"{k}={v}" for k, v in s.items() if k != "nodes")
        print(f"  {t:<20} {s['nodes']:>4}" + (f"   ({extra})" if extra else ""))
    print("\nRelation columns (matched / total names)")
    for (t, col, rel), (m, n) in col_stats.items():
        pct = (m / n) if n else 1.0
        flag = "   <-- check names" if pct < LOW_MATCH else ""
        print(f"  {t}.{col} [{rel}]: {m}/{n} ({pct:.0%}){flag}")
        for tok, c in unmatched[(t, col)].most_common(5):
            print(f"      unmatched: {tok!r} x{c}")
    print(f"\n{len(edges)} unique edges ready.")


# ---------------------------------------------------------------- database
def report(cur):
    cur.execute("SELECT type, count(*) FROM nodes GROUP BY 1 ORDER BY 1")
    print("\nNodes in DB:")
    for t, n in cur.fetchall():
        print(f"  {t:<20} {n:>4}")
    cur.execute("SELECT rel_type, count(*) FROM edges GROUP BY 1 ORDER BY 1")
    print("\nEdges in DB:")
    for rel, n in cur.fetchall():
        print(f"  {rel:<14} {n:>5}")
    cur.execute(
        """SELECT type, count(*) FROM nodes n
           WHERE NOT EXISTS (SELECT 1 FROM edges e WHERE e.src_id = n.id OR e.dst_id = n.id)
           GROUP BY 1 ORDER BY 1"""
    )
    orphans = cur.fetchall()
    print("\nNodes with no edges:", ", ".join(f"{t}={n}" for t, n in orphans) or "none")


def load_db(nodes, edges):
    from sentence_transformers import SentenceTransformer

    print("\nLoading all-MiniLM-L6-v2 (384-dim)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    items = list(nodes.values())
    texts = [n["text"] for n in items]

    lengths = [len(ids) for ids in model.tokenizer(texts, truncation=False)["input_ids"]]
    long_rows = [items[i]["name"] for i, n in enumerate(lengths) if n > model.max_seq_length]
    if long_rows:
        print(f"{len(long_rows)} rows exceed {model.max_seq_length} tokens; the tail is not embedded "
              f"(e.g. {long_rows[:3]}).")
    vecs = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=True)

    conn = psycopg2.connect(**DB_PARAMS)
    register_vector(conn)
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE nodes DROP CONSTRAINT IF EXISTS nodes_type_check")
            cur.execute("ALTER TABLE nodes ADD CONSTRAINT nodes_type_check CHECK (type IN %s)", (tuple(NODE_TYPES),))
            cur.execute("TRUNCATE edges, nodes RESTART IDENTITY")
            execute_values(
                cur,
                "INSERT INTO nodes (type, name, description, embedding, metadata) VALUES %s",
                [(n["type"], n["name"], n["desc"], v, Json(n["meta"])) for n, v in zip(items, vecs)],
                page_size=200,
            )
            cur.execute("SELECT id, type, name FROM nodes")
            ids = {(t, norm(nm)): i for i, t, nm in cur.fetchall()}
            rows = sorted({(ids[a], ids[b], rel) for a, b, rel in edges})
            execute_values(
                cur,
                "INSERT INTO edges (src_id, dst_id, rel_type) VALUES %s ON CONFLICT DO NOTHING",
                rows,
                page_size=500,
            )
            report(cur)
        conn.commit()
        print("\nCommitted.")
    except Exception:
        conn.rollback()
        print("\nFAILED: rolled back, database unchanged.")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------- hops + search
# Walks edges in BOTH directions and prints each path with the real arrow direction, so every
# hop shown is an actual stored relationship. No node repeats within a path.
HOPS_SQL = """
WITH RECURSIVE walk AS (
  SELECT id, ARRAY[id] AS seen, name || ' (' || type || ')' AS path, 0 AS depth, type
  FROM nodes WHERE lower(name) = lower(%(name)s)
  UNION ALL
  SELECT t.id, w.seen || t.id,
         w.path
           || CASE WHEN x.fwd THEN ' -[' || x.rel_type || ']-> ' ELSE ' <-[' || x.rel_type || ']- ' END
           || t.name || ' (' || t.type || ')',
         w.depth + 1, t.type
  FROM walk w
  CROSS JOIN LATERAL (
    SELECT dst_id AS nid, rel_type, true AS fwd FROM edges WHERE src_id = w.id
    UNION ALL
    SELECT src_id, rel_type, false FROM edges WHERE dst_id = w.id
  ) x
  JOIN nodes t ON t.id = x.nid
  WHERE w.depth < %(depth)s AND t.id <> ALL (w.seen)
)
SELECT depth, path, n FROM (
  SELECT depth, path,
         count(*) OVER (PARTITION BY depth) AS n,
         row_number() OVER (PARTITION BY depth ORDER BY path) AS rn
  FROM walk
  WHERE depth > 0 AND (%(to)s::text IS NULL OR type = %(to)s::text)
) s
WHERE rn <= %(limit)s
ORDER BY depth, rn
"""


def query_mode(args):
    conn = psycopg2.connect(**DB_PARAMS)
    register_vector(conn)
    cur = conn.cursor()
    if args.search:
        from sentence_transformers import SentenceTransformer

        vec = SentenceTransformer("all-MiniLM-L6-v2").encode(args.search, normalize_embeddings=True)
        cur.execute(
            "SELECT type, name, 1 - (embedding <=> %s) FROM nodes ORDER BY embedding <=> %s LIMIT 5",
            (vec, vec),
        )
        print(f"Closest nodes to {args.search!r}:")
        for t, name, sim in cur.fetchall():
            print(f"  {sim:.3f}  {name} ({t})")
    if args.hops:
        cur.execute(HOPS_SQL, {"name": args.hops, "depth": args.depth, "to": args.to, "limit": args.limit})
        rows = cur.fetchall()
        if not rows:
            print(f"No paths from {args.hops!r}. Check the exact name (try --search).")
        last = None
        for depth, path, n in rows:
            if depth != last:
                print(f"\n== {depth} hop(s): {n} paths (showing up to {args.limit}) ==")
                last = depth
            print("  " + path)
    conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="cleaned", help="folder with the cleaned CSVs (default: cleaned)")
    ap.add_argument("--dry-run", action="store_true", help="parse and match only; no model, no DB")
    ap.add_argument("--hops", metavar="NAME", help="print paths starting from this node name")
    ap.add_argument("--depth", type=int, choices=[1, 2, 3], default=2, help="max hops (default 2)")
    ap.add_argument("--to", choices=NODE_TYPES, help="only show paths that END at this node type")
    ap.add_argument("--limit", type=int, default=15, help="paths to print per hop count (default 15)")
    ap.add_argument("--search", metavar="TEXT", help="semantic search over node descriptions")
    args = ap.parse_args()

    if args.hops or args.search:
        return query_mode(args)

    tables = read_tables(args.dir)
    nodes, stats = build_nodes(tables)
    edges, col_stats, unmatched = build_edges(tables, nodes)
    print_parse_report(stats, col_stats, unmatched, edges)
    if not args.dry_run:
        load_db(nodes, edges)


if __name__ == "__main__":
    main()