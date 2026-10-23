# FIA Baseline Demo: Postgres + pgvector

Baseline for the FIA Insight Engine knowledge base. One Postgres database with
pgvector, using a generic `nodes` / `edges` schema that mirrors the FIA framework graph.

**Status:** working end to end. The cleaned Notion CSVs load into 731 nodes (with
384-dimension embeddings) and 3,356 edges, and multi-hop paths and semantic search both run.

## Prerequisites

- **Docker Desktop** (includes Docker Compose). Install it, open it, and wait until it says it is running.
  Check with: `docker --version` and `docker compose version`
- **Git**, to clone this repo
- **Python 3.10+** with these packages:
```bash
  pip install pandas psycopg2-binary pgvector python-dotenv sentence-transformers
```
   (`sentence-transformers` is large because it pulls in PyTorch. The first load also
   downloads the ~90 MB `all-MiniLM-L6-v2` model.)
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

- **`nodes`**: `id`, `type`, `name`, `description`, `embedding vector(384)`.
  `type` is one of: player_type, red_flag, abuse_technique, vulnerability_trait,
  trauma_pathway, mental_process, media_character, flavor_of_abuse.
  `(type, name)` is unique and descriptions cannot be empty.
- **`edges`**: `src_id`, `dst_id`, `rel_type`.

| rel_type | From | To |
|---|---|---|
| HAS_RED_FLAG | player_type | red_flag |
| USES | player_type | abuse_technique |
| TARGETS | player_type | vulnerability_trait |
| EXPLOITS | abuse_technique | vulnerability_trait |
| PRODUCES | abuse_technique | trauma_pathway |
| ACCOMPANIES | red_flag | abuse_technique |
| OPERATES_IN | flavor_of_abuse | player_type |
| EXEMPLIFIES | media_character | player_type |

Embeddings use `all-MiniLM-L6-v2` (384 dimensions) with cosine distance
(HNSW index). Changing the model or dimension means re-embedding all data.

**Schema note:** `unes_trait` is not yet in the CHECK constraint in `schema.sql`.
> `load_graph.py` adds it to the constraint each time it runs. Update `schema.sql` once
> the node-type decisions below are final so a fresh database matches what the loader expects.
Still open: whether UNES is a node type or a set of properties, and what
edges Mental Processes should have.

## Everyday commands

```bash
docker compose stop              # stop, keep data
docker compose start             # start again
docker compose down -v           # wipe everything, including the database
docker compose logs fia-pg       # view logs
```

## Data pipeline

Raw Notion CSVs go through two steps so far: clean, then check what remains.
Neither step modifies the original export.

| Step | Script | Input | Output |
|------|--------|-------|--------|
| 1. Clean | `clean.py` | `notion_export/` | `cleaned/` + `cleaned/cleanup_report.md` |
| 2. Visualize | `visualize.py` | `cleaned/` | Column summary printed in the terminal |
| 3. Load graph | `load_graph.py` | `cleaned/` | Rows in `nodes` and `edges` |
| 4. Query | `load_graph.py --hops / --search` | database | Paths and nearest nodes printed in the terminal |

### Run it

```bash
pip install pandas

# 1. Clean: drops empty/sparse columns, fills empty property cells with NULL,
#    saves files under clean names (no Notion id suffix)
python clean.py notion_export/ --out cleaned/

# 2. Visualize: shows what is left in each cleaned file
python visualize.py

# 3. Load the graph
python fia-baseline/load_graph.py --dry-run   # parse and match names only; no database, no model
python fia-baseline/load_graph.py             # rebuild nodes, embeddings and edges
```

### What clean.py does
- Turns placeholders (N/A, TBD, -, ?, null) into empty cells.
- Drops rows with no Name.
- Drops columns that are empty or under 1% filled (change with `--min-fill`).
- Fills remaining empty cells with `NULL`, but never in Name, description, or relation columns.
- Saves each file under its clean name and lists original -> saved names in the report.

### How to read the visualize output
For each category it lists every column with the number of real values, the number of cells
filled with NULL, and a sample value. Use it to confirm the right columns survived and to spot
columns that are mostly NULL.

### What load_graph.py does
Use `--dir <folder>` if `cleaned/` is not in the folder you run the command from.
 
What the loader does:
 
- **Every named row becomes a node.** If a row has no real description, one is composed
  from its other text fields and `metadata.description_synthesized` is set to `true`.
- **Relation columns become edges.** Names are split on commas (re-joining names that
  contain commas), Notion URLs are removed, and names are matched to nodes of the expected
  type. Both sides of a Notion relation are read and duplicates collapse.
- **Full rebuild in one transaction.** Each run empties `edges` and `nodes` and reloads them.
  If anything fails, the database is left unchanged.
- **Report.** It prints node counts, per-column match rates with unmatched names, edge
  counts per type, and nodes with no edges.

The relation mapping is the `RELATIONS` list at the top of `load_graph.py`; each entry is one line.

### 4. Query: multi-hop paths and semantic search
 
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
 
Every line of a path is a stored relationship, shown with its real direction. Example:
 
```
Mr. Always Right (player_type) -[USES]-> Belittling (abuse_technique) -[EXPLOITS]-> People-pleasing (vulnerability_trait)
```
 
For each hop count the output also shows how many paths exist in total.
 
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
5. **Semantic search.** `--search "love bombing"` should return a relevant technique near the top.
6. **Repeatability.** Run the load twice; counts should be identical.

## Known data gaps
 
These come from the Notion data, not the scripts.
 
- **71 relation entries exported as "Untitled"** (53 in Player typologies "He might use these
  techniques", 17 in Vulnerability Traits "Abuse Techniques", 1 in Mental processes "Abuse
  Techniques"). They point to pages whose titles did not export, so those edges are missing.
- **Nodes with no edges** cannot appear in any hop: 37 trauma_pathway, 29 vulnerability_trait,
  18 abuse_technique, 17 mental_process, 3 red_flag, 2 unes_trait, 1 player_type.
- **Composed descriptions.** Rows without a real description get one built from their other
  fields, so semantic search is weaker on those types: all 141 red flags, 80 trauma rows, 90 of
  91 vulnerability traits, 26 media characters, 14 mental processes (counted before duplicate
  names are merged).
- **Duplicate names.** One each in Media characters, Trauma and Vulnerability Traits (for
  example "Empathic women who over-accommodate") merge into a single node; the last row wins
  for description and metadata.
- **Typos in names** (for example "Austistic" and "Empathatic" in Vulnerability Traits) show up
  as-is in results. Fix them in Notion and re-export.
- **Relations that are not two-way.** Abuse technique <-> UNES trait is listed on both sides
  but the two sides do not agree (690 links from UNES, 150 from Abuse Techniques); the loader
  takes the union. Media characters <-> player types is similar.
## Open decisions
 
- **UNES:** currently loaded as its own node type (`unes_trait`). The original plan left open
  whether it should be a node type or a set of properties.
- **Mental Processes edges:** currently `EXPLOITS` to vulnerability traits and `OPERATES_IN`
  from abuse techniques. `OPERATES_IN` is a loose fit; a dedicated relation type may be clearer.
- **Flavors of abuse:** `flavor_of_abuse` exists in the schema but there is no source file.
  Flavors currently appear only as text in node metadata, with no nodes or edges.
- **Brain biases:** appear as text columns in two files but have no source table, so they have
  no nodes or edges.
- **Untitled relations:** decide whether to repair them in Notion or accept the missing edges.

## Notes

- `clean.py` known issue: `--min-fill 0.0` keeps empty columns instead of dropping them.
- Rows with an empty description are listed in `cleanup_report.md`. They are left blank on purpose.
- `notion_export/` and `cleaned/` are git-ignored because they contain FIA content.