# FIA Baseline Demo: Postgres + pgvector

Baseline for the FIA Insight Engine knowledge base. One Postgres database with
pgvector, using a generic `nodes` / `edges` schema that mirrors the FIA framework graph.

**Status:** working end to end. The cleaned Notion CSVs load into 731 nodes (with
384-dimension embeddings) and 3,356 edges, and multi-hop paths and semantic search both run.

## Prerequisites

- **Docker Desktop** (includes Docker Compose). Install it, open it, and wait until it says it is running.
  Check with: `docker --version` and `docker compose version`
- **Git**, to clone this repo
- **Python 3.10+** with the packages in `requirements.txt`:
  ```bash
  python -m pip install -r requirements.txt
  ```
  (`sentence-transformers` is large because it pulls in PyTorch. The first load also
  downloads the ~90 MB `all-MiniLM-L6-v2` model. `clean.py` needs no packages at all.)
- Port **[5433]** free on your machine (change the left side of the port mapping in
  `docker-compose.yml` if something else is using it)

## Quick start

All commands run from the repo root (`FIA_Data_pipeline`).

1. Clone the repo and open the folder:
   ```bash
   git clone [REPO_URL]
   cd FIA_Data_pipeline
   ```

2. Create your `.env` file. The file must be named exactly `.env`, not `general.env` or `.env.txt`:
   ```
   POSTGRES_PASSWORD=choose_a_password
   POSTGRES_DB=fia
   ```
   `.env.example` shows the format. Never commit `.env`.

3. Start the database:
   ```bash
   docker compose up -d
   ```
   On the first start, Docker creates the database and runs `schema.sql` automatically.
   `schema.sql` only runs when the data volume is empty. To re-run it after changing it,
   use `docker compose down -v` first (this deletes all data).

4. Verify it worked:
   ```bash
   docker compose exec fia-pg psql -U postgres -d fia -c "\dt"
   ```
   You should see two tables: `nodes` and `edges`.

5. Put your Notion CSV exports in `notion_export/`, then build the graph (see
   [Data pipeline](#data-pipeline)):
   ```bash
   python fia-baseline/clean.py notion_export/ --out cleaned/ --fill ""
   python fia-baseline/load_graph.py --dry-run
   python fia-baseline/load_graph.py
   ```
   (`--fill ""` leaves empty cells blank. The loader treats blank and `NULL` the same.)

   > **Check `cleaned/cleanup_report.md` before loading.** It shows most data problems:
   > empty descriptions, duplicate names, very short or reused descriptions, dropped
   > columns, and rows with no name. Every finding is also in `cleaned/cleanup_issues.csv`.

6. Try a multi-hop query:
   ```bash
   python fia-baseline/load_graph.py --hops "Mr. Always Right" --depth 2 --to vulnerability_trait
   ```

## Connecting

| Setting  | Value |
|----------|-------|
| Host     | `127.0.0.1` |
| Port     | `[5433]` |
| Database | `fia` |
| User     | `postgres` |
| Password | the value in your `.env` |

Connection string:
```
postgresql://postgres:<password>@localhost:[5433]/fia
```
In a database client (DBeaver, etc.), choose **PostgreSQL**, not MySQL.

## Schema

- **`nodes`**: `id`, `type`, `name`, `description`, `embedding vector(384)`, `metadata JSONB`
  (the other columns of the source row, plus `description_synthesized` when the description was
  composed by the loader).
  `type` is one of: player_type, red_flag, abuse_technique, vulnerability_trait,
  trauma_pathway, mental_process, media_character, flavor_of_abuse. The loader also allows
  `unes_trait` (see the schema note below).
  `(type, name)` is unique and descriptions cannot be empty.
- **`edges`**: `src_id`, `dst_id`, `rel_type`.

These are the relationships the loader builds (the `RELATIONS` list at the top of `load_graph.py`
is the source of truth):

| rel_type | From | To |
|---|---|---|
| HAS_RED_FLAG | player_type | red_flag |
| USES | player_type | abuse_technique |
| TARGETS | player_type | vulnerability_trait |
| EXPLOITS | abuse_technique | vulnerability_trait |
| EXPLOITS | mental_process | vulnerability_trait |
| PRODUCES | player_type | trauma_pathway |
| PRODUCES | abuse_technique | trauma_pathway |
| ACCOMPANIES | red_flag | unes_trait |
| ACCOMPANIES | abuse_technique | unes_trait |
| OPERATES_IN | abuse_technique | mental_process |
| EXEMPLIFIES | media_character | player_type |

Embeddings use `all-MiniLM-L6-v2` (384 dimensions) with cosine distance
(HNSW index). Changing the model or dimension means re-embedding all data.

**Schema note:** `unes_trait` is not yet in the CHECK constraint in `schema.sql`.
`load_graph.py` adds it to the constraint each time it runs. Update `schema.sql` once
the node-type decisions below are final so a fresh database matches what the loader expects.

## Everyday commands

```bash
docker compose stop              # stop, keep data
docker compose start             # start again
docker compose down -v           # wipe everything, including the database
docker compose logs fia-pg       # view logs
```

## Data pipeline

Raw Notion CSVs go through four steps. No step modifies the original export.

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1. Clean | `clean.py` | `notion_export/` | `cleaned/` + `cleaned/cleanup_report.md` + `cleaned/cleanup_issues.csv` |
| 2. Inspect | `visualize.py` | `cleaned/` | Column summary printed in the terminal |
| 3. Load graph | `load_graph.py` | `cleaned/` | Rows in `nodes` and `edges` |
| 4. Query | `load_graph.py --hops / --search` | database | Paths and nearest nodes printed in the terminal |

### Where to see data problems

> **Start with `cleaned/cleanup_report.md`.** It is the quickest way to see what is wrong with
> the export before anything is loaded. The report is rewritten every time you run `clean.py`.

| What you want to see | Where |
|---|---|
| Empty descriptions, by file | `cleanup_report.md`, "Empty descriptions by file" (each row is in `cleanup_issues.csv`) |
| Duplicate names | `cleanup_report.md`, "Duplicate names" |
| Very short or reused descriptions | `cleanup_report.md`, "Very short descriptions" and "Reused descriptions" |
| Rows with no name, duplicate column titles, a missing Name column | `cleanup_report.md`, "Structural checks" and the sections under it |
| Dropped columns, cells filled, placeholders cleared, saved file names | `cleanup_report.md`, the summary tables at the top |
| Every individual finding, filterable | `cleanup_issues.csv` (opens in Excel) |
| Names that matched nothing, per-column match rates, nodes with no edges | the loader's report (step 3), not the cleanup report |

### Run it

```bash
# 1. Clean: structural cleanup and checks (see below)
python fia-baseline/clean.py notion_export/ --out cleaned/

# 2. Inspect: shows what is left in each cleaned file
python fia-baseline/visualize.py

# 3. Load the graph
python fia-baseline/load_graph.py --dry-run   # parse and match names only; no database or model,
                                              # but the packages must still be installed
python fia-baseline/load_graph.py             # rebuild nodes, embeddings and edges
```

Use `--dir <folder>` with `load_graph.py` if `cleaned/` is not in the folder you run the command from.
Read `cleaned/cleanup_report.md` after step 1 and the match report after step 3 before moving on.

### What clean.py does

Structural cleanup only. Relationship problems are reported by the loader.

- Turns placeholders (N/A, TBD, -, ?, null) into empty cells (counted in "Placeholders Cleared").
- Drops rows with no Name (listed by line number).
- Drops columns that are empty or under 1% filled (change with `--min-fill`).
- Fills remaining empty cells with `NULL` (default; `--fill ""` disables), but never in Name,
  description, or relation columns.
- Saves each file under its clean name and lists original -> saved names in the report.
- Checks structure and reports it (counts and examples in `cleanup_report.md`, every finding in
  `cleanup_issues.csv`):
  - duplicate names within a file
  - empty descriptions, or a file with no description column
  - very short descriptions (under 15 characters; change with `--min-desc`, `0` disables)
  - the same description reused by different rows
  - duplicate column titles, or a file with no Name column

### How to read the inspect output (visualize.py)
For each category it lists every column with the number of real values, the number of cells
filled with NULL, and a sample value. Use it to confirm the right columns survived and to spot
columns that are mostly NULL.

### What load_graph.py does

- **Every named row becomes a node.** If a row has no real description, one is composed
  from its other text fields and `metadata.description_synthesized` is set to `true`.
- **Relation columns become edges.** Names are split on commas (re-joining names that
  contain commas), Notion URLs are removed, and names are matched to nodes of the expected
  type. Both sides of a Notion relation are read and duplicates collapse.
- **Full rebuild in one transaction.** Each run empties `edges` and `nodes` and reloads them.
  If anything fails, the database is left unchanged. The CSVs are the source of truth, so
  anything edited by hand in the database is lost on the next load.
- **Report.** It prints node counts, per-column match rates with unmatched names, edge
  counts per type, and nodes with no edges.

The relation mapping is the `RELATIONS` list at the top of `load_graph.py`; each entry is one line.

### Query: multi-hop paths and semantic search

```bash
# Paths from a node, following edges in both directions
python fia-baseline/load_graph.py --hops "Mr. Always Right" --depth 2
# Only paths that end at a given node type
python fia-baseline/load_graph.py --hops "Mr. Always Right" --depth 2 --to vulnerability_trait
# Longer chains (depth 1 to 3) and more rows per hop count
python fia-baseline/load_graph.py --hops "Trusting" --depth 3 --limit 30
# Find a node by meaning
python fia-baseline/load_graph.py --search "manipulative behavior and control"
```

Every arrow in a path is a stored relationship, shown with its real direction. Example:

```
Mr. Always Right (player_type) -[USES]-> Belittling (abuse_technique) -[EXPLOITS]-> People-pleasing (vulnerability_trait)
```

For each hop count the output also shows how many paths exist in total.

Tip: depth 3 from a well-connected node can produce a very large number of paths, and paths can
route through highly connected nodes such as UNES traits. Use `--to` to keep results readable.

## Testing

Open a SQL session:

```bash
docker compose exec fia-pg psql -U postgres -d fia
```

1. **Edge directions and types.** Only sensible type pairs should appear:
   ```sql
   SELECT n1.type AS src, e.rel_type, n2.type AS dst, count(*)
   FROM edges e JOIN nodes n1 ON n1.id = e.src_id JOIN nodes n2 ON n2.id = e.dst_id
   GROUP BY 1,2,3 ORDER BY 2,1,3;
   ```
2. **Embeddings.** Expected result is `0, 384, 384`:
   ```sql
   SELECT count(*) FILTER (WHERE embedding IS NULL) AS missing,
          min(vector_dims(embedding)), max(vector_dims(embedding)) FROM nodes;
   ```
3. **Hops against the source data.** Run `--hops` for a well-connected node, then check a few
   printed paths by hand in the CSVs (the technique is in the player type's "He might use these
   techniques" cell, and the trait's "Abuse Techniques" cell lists that technique).
4. **Reverse direction.** `--hops "Trusting" --depth 2 --to player_type` should show
   `<-[TARGETS]-` arrows and match the trait's "Player typologies" cell.
5. **Semantic search.** `--search "love bombing"` should return a relevant technique in the top 5.
6. **Repeatability.** Run the load twice; counts should be identical.
7. **No placeholder nodes.** Notion exports untitled pages as "Untitled". Expected result is no rows:
   ```sql
   SELECT type, name FROM nodes WHERE name ILIKE 'untitled%';
   ```

## Known data gaps

These come from the Notion data, not the scripts. **Many of them can be seen in
`cleaned/cleanup_report.md`** (empty descriptions and duplicate names, below); every finding is
in `cleanup_issues.csv`. Names that matched nothing are listed by the loader's match report.

- **71 relation entries exported as "Untitled"** (53 in Player typologies "He might use these
  techniques", 17 in Vulnerability Traits "Abuse Techniques", 1 in Mental processes "Abuse
  Techniques"). They point to pages whose titles did not export, so those edges are missing.
  The 53 in "He might use these techniques" feed the `USES` edges (player type to technique), the
  core path for traversal tests, so repair them in Notion before the sponsor demo or any timing
  measurements.
- **Nodes with no edges** cannot appear in any hop: 37 trauma_pathway, 29 vulnerability_trait,
  18 abuse_technique, 17 mental_process, 3 red_flag, 2 unes_trait, 1 player_type.
- **Composed descriptions.** Rows without a real description get one built from their other
  fields, so semantic search is weaker on those types: all 141 red flags, 80 trauma rows, 90 of
  91 vulnerability traits, 26 media characters, 14 mental processes (counted before duplicate
  names are merged). Keep this in mind when judging search relevance on these types. Real
  descriptions would improve results more than changing the embedding model. See "Empty
  descriptions by file" in `cleanup_report.md`.
- **Duplicate names.** One each in Media characters, Trauma and Vulnerability Traits (for
  example "Empathic women who over-accommodate") merge into a single node; the last row wins
  for description and metadata. Listed under "Duplicate names" in `cleanup_report.md`.
- **Typos in names** (for example "Austistic" and "Empathatic" in Vulnerability Traits) show up
  as-is in results. Fix them in Notion and re-export. The loader's list of unmatched names can
  help find them.
- **Relations that are not two-way.** Abuse technique <-> UNES trait is listed on both sides
  but the two sides do not agree (690 links from UNES, 150 from Abuse Techniques); the loader
  takes the union. Media characters <-> player types is similar.

## Open decisions

- **UNES:** currently loaded as its own node type (`unes_trait`). The original plan left open
  whether it should be a node type or a set of properties. Because UNES links are numerous,
  the choice also changes how many paths a traversal returns.
- **Union or intersection for one-sided relations:** the loader keeps every link listed by either
  side. Keeping only links both sides agree on would give a much smaller graph.
- **Mental Processes edges:** currently `EXPLOITS` to vulnerability traits and `OPERATES_IN`
  from abuse techniques. `OPERATES_IN` is a loose fit; a dedicated relation type may be clearer.
- **Relations from the framework document that are not loaded:** red flag to abuse technique
  (the loader uses `ACCOMPANIES` for red flag to UNES trait instead) and flavor of abuse to
  player type (uses `OPERATES_IN`, which is currently abuse technique to mental process).
  Decide whether to restore them or rename the relation types.
- **Flavors of abuse:** `flavor_of_abuse` exists in the schema but there is no source file.
  Flavors currently appear only as text in node metadata, with no nodes or edges.
- **Brain biases:** appear as text columns in two files but have no source table, so they have
  no nodes or edges.
- **Untitled relations:** decide whether to repair them in Notion or accept the missing edges.

## Notes

- `clean.py` known issue: `--min-fill 0.0` keeps empty columns instead of dropping them. Use a
  small value such as `--min-fill 0.001` to drop columns that are completely empty.
- Rows with an empty description are listed in `cleanup_report.md` and `cleanup_issues.csv`. They
  are left blank on purpose; the loader composes a description for them.
- `.env`, `notion_export/` and `cleaned/` are git-ignored because they contain secrets or FIA
  content. Add `__pycache__/` to `.gitignore` too.