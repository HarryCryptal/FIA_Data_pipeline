# FIA Baseline Demo: Postgres + pgvector

Baseline for the FIA Insight Engine knowledge base. One Postgres database with
pgvector, using a generic `nodes` / `edges` schema that mirrors the FIA framework graph.

## Prerequisites

- **Docker Desktop** (includes Docker Compose). Install it, open it, and wait until it says it is running.
  Check with: `docker --version` and `docker compose version`
- **Git**, to clone this repo
- **Python 3.10+**, only needed later for the import script
- Port **[5433]** free on your machine (change the left side of the port mapping in
  `docker-compose.yml` if something else is using it)

## Quick start

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

4. Verify it worked:
```bash
   docker compose exec fia-pg psql -U postgres -d fia -c "\dt"
```
   You should see two tables: `nodes` and `edges`.

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

Still open: whether UNES is a node type or a set of properties, and what
edges Mental Processes should have.

## Everyday commands

```bash
docker compose stop              # stop, keep data
docker compose start             # start again
docker compose down -v           # wipe everything, including the database
docker compose logs fia-pg       # view logs
```
