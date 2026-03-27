# UltraBot v2 — Project Context

> **Last updated:** 2026-03-27  
> **Root:** `d:\Projects\UltraBot v2`  
> **Language:** Python 3.12+ · **Framework:** discord.py (slash commands)  
> **Database:** MySQL (`ultrabotdbd` on localhost via PyMySQL)  
> **LLM:** Ollama (local, llama3 model)  
> **Vector DB:** ChromaDB (persistent, cosine similarity)  
> **Env vars:** `.env` (`DISCORD_TOKEN`, `SQL_PASSWORD`)

---

## Purpose

A **Discord bot** primarily focused on the game **Dead by Daylight (DBD)**.  
Core features: random/weighted perk builds, per-user blacklists, perk synergy via RAG+LLM, match result tracking, auto-updating perk data from the wiki, and a music player.

---

## Naming Conventions

- **Hungarian-ish prefix style**: methods start with `m` (e.g., `mGetRandomBuild`), parameters start with `a` (e.g., `aCtx`), private members use `__` + `_camelCase`.
- **File-level free functions** also use `m` prefix.
- **Constants** are `UPPER_SNAKE_CASE` on classes.

---

## Directory Structure

```
UltraBot v2/
├── main.py                        # Entry point: Runner class
├── .env                           # DISCORD_TOKEN, SQL_PASSWORD
├── requirements.txt               # Dependencies (utf-16 encoded)
│
├── config/
│   ├── dbdconfig.json             # DBD asset paths, Ollama URL/model, intervals
│   ├── hctasks.json               # Healthcheck scheduled tasks + last_run timestamps
│   ├── musicconfig.json           # Music config
│   └── definitions.py             # CogNames enum (mostly unused)
│
├── log/
│   ├── logger.py                  # Custom logging: info/error/trace/discord file handlers
│   ├── info.log, error.log, trace.log, discord.log
│
├── cogs/                          # Discord cog layer (slash commands)
│   ├── dbd.py                     # Main cog: 16 slash commands (see below)
│   ├── musicplayer.py             # /play, /stop, etc.
│   ├── fun.py, utils.py           # Minor cogs
│   └── minecraft.py, morse.py, translation.py  # Stub cogs
│
├── entities/
│   ├── bot.py                     # Bot initialization, cog loading, on_ready sync
│   │
│   ├── handlers/                  # Thin facade layer between cogs and workers
│   │   ├── dbd.py                 # DbdHandler: singleton, TTLCache of DbdWorkers
│   │   ├── buttons.py             # ResultsButtons: Win/Loss buttons on builds
│   │   └── fun.py                 # Fun handler
│   │
│   ├── workers/                   # Business logic layer
│   │   ├── dbd/
│   │   │   ├── worker.py          # DbdWorker: per-user, owns PerkTracker + SQLRetriever
│   │   │   ├── perks.py           # PerkTracker: weighted random, blacklist, exhaustion
│   │   │   └── rag.py             # RAG pipeline: ChromaDB + BM25 + RRF hybrid retrieval
│   │   ├── utils/
│   │   │   └── healthcheck.py     # HealthWorker: scheduled tasks (cleanup, scrape, RAG)
│   │   ├── music/music.py
│   │   └── fun/worker.py
│   │
│   └── utils/                     # Shared utilities
│       ├── sql.py                 # SQLRetriever: all MySQL queries
│       ├── files.py               # File I/O, config helpers, GDrive download, cleanup
│       ├── images.py              # PIL collage creation
│       ├── datahandler.py         # DBDDataHandler: matplotlib animated plots
│       ├── dbdwebscraper.py       # DBDScraper: wiki → DB perk sync
│       ├── rare.py                # String matching (rapidfuzz, jellyfish, Levenshtein)
│       └── musicutils.py          # YouTube / yt-dlp helpers
│
├── assets/dbd/
│   ├── chroma_db/                 # Persistent ChromaDB storage
│   ├── data/                      # DBD data files
│   ├── imgs/perks/                # Perk icon PNGs (named by UUID)
│   └── llm_perk.json             # {perk_name: description} for RAG
│
├── sql/
│   └── create_perk_weights.sql    # perk_weights table DDL
│
└── tests/
    ├── test_perks.py
    ├── test_rag_hybrid.py
    └── test_rare*.py
```

---

## Architecture Flow

```
User → Discord slash command → Cog (cogs/dbd.py)
  → DbdHandler (entities/handlers/dbd.py) — singleton, TTLCache(500, 1h)
    → DbdWorker (entities/workers/dbd/worker.py) — per-user instance
      → PerkTracker     — weighted random sampling, blacklist management
      → SQLRetriever    — all MySQL queries
      → DBDRagPipeline  — synergy builds via RAG + Ollama LLM
      → Image utils     — PIL collage generation
```

### Key Design Patterns
- **Singleton handler**: `DbdHandler.__new__` ensures one instance.
- **TTLCache workers**: `DbdWorker` instances cached per user ID, evicted after 1 hour.
- **Weighted random**: Perks have weights (0.0–1.0); selected perks decay, all recover each roll. Category diversity is softly penalized. Max 1 exhaustion perk per build.
- **Hybrid RAG retrieval**: Semantic (ChromaDB `all-MiniLM-L6-v2`) + keyword (BM25) fused via Reciprocal Rank Fusion.

---

## DBD Slash Commands (`cogs/dbd.py`)

| Command | Description |
|---|---|
| `/dbdrandom` | Random 4-perk build (weighted) |
| `/dbdsuggest <type>` | Build of a type (LOOP, RUSH, INFO, SLUG, TUNNEL, SUPPORT) |
| `/dbdsynergy <perk>` | Synergy build via RAG + Ollama around a specific perk |
| `/dbdretry <index>` | Re-roll specific perk(s) in current build |
| `/dbdban <index>` | Blacklist + re-roll specific perk(s) |
| `/dbdbye <index/name>` | Blacklist a perk (no re-roll) |
| `/dbdadd <perk>` | Un-blacklist a perk |
| `/dbdbanlist` | Show user's blacklisted perks |
| `/dbdhelp <index/name>` | Show perk info (owner, categories, effect, image) |
| `/dbdimg <name>` | Show perk image |
| `/dbdset <perks>` | Set a custom 4-perk build |
| `/dbdmystats` | User's match statistics |
| `/dbdstats` | Global match statistics |
| `/dbdupdate` | Admin: manual wiki scrape |
| `/dbdkill` | Admin: shutdown bot + Ollama |
| `/ping` | Latency check |

---

## MySQL Schema (`ultrabotdbd`)

### Tables (inferred from SQL queries)
| Table | Key Columns |
|---|---|
| `users` | `id` (BIGINT PK), `name` |
| `characters` | `id` (auto PK), `name`, `gender` |
| `perks` | `id` (auto PK), `uuid`, `name`, `owner_id` → characters, `main_effect`, `is_exhaustion` |
| `types` | `id`, `type` (LOOP, RUSH, etc.) |
| `perk_types` | `perk_id` → perks, `type_id` → types |
| `blacklists` | `user_id` → users, `perk_name` → perks.name |
| `perk_weights` | `user_id` + `perk_name` (composite PK), `weight` FLOAT |
| `matches` | `user` → users, `outcome` (ESCAPE/DEATH), `match_date`, `perk_1_name`…`perk_4_name` |

---

## Healthcheck / Scheduled Tasks (`healthcheck.py`)

Runs on a daemon thread, checks every 1 minute:

| Task | Interval | Action |
|---|---|---|
| `cleanup_dbd_generated_imgs` | 15 min | Delete old generated collage images |
| `update_dbd_perks` | 1440 min (24h) | Scrape wiki → update DB + download perk images |
| `cleanup_dbd_rag_data` | 1440 min (24h) | Clear `llm_perk.json` + ChromaDB collection |

Task state persisted in `config/hctasks.json`.

---

## RAG Pipeline (`rag.py`)

1. **`init_llm_perk_data()`** — Creates `llm_perk.json` from DB perk data (name → description).
2. **`init_chromadb()`** — Embeds all perk descriptions using `all-MiniLM-L6-v2`, stores in ChromaDB with cosine similarity. Also builds a `BM25Scorer` from the same corpus.
3. **`retrieve_hybrid()`** — Queries both ChromaDB (semantic) and BM25 (keyword), fuses results via RRF (k=60), returns top-k perk names.
4. **Synergy build flow** (`DbdWorker.mGetSynergyBuild`):
   - Resolve perk name → get description
   - Hybrid retrieval → top 20 similar perks (excluding blacklist)
   - Prompt Ollama for a 4-perk build (JSON format enforced)
   - Validate LLM response against whitelist, fallback to random for any invalid perks
   - Generate collage + return explanation

---

## Key Utility Modules

### `rare.py` — String Matching
- `mFindMostSimilarPartial()` — Best match using `rapidfuzz.fuzz.partial_ratio`
- `mListMostSimilarPartial()` — Top N matches above threshold 55
- `mFindMostSimilarJelly()` — Damerau-Levenshtein via jellyfish
- `mSuperCleanString()` — Normalize accents, strip non-alpha, lowercase

### `files.py` — File I/O
- `mGetAssetsDir()` / `mGetBaseDir()` — Resolve paths relative to `entities/utils/`
- `mGetDBDConfig()` → parses `config/dbdconfig.json`
- `mGetConfigProperty(key)` → shorthand for config lookups
- `mCleanupDir()` — Delete files older than N minutes
- `mDownloadFromGDrive()` — Download by Google Drive file ID

### `images.py` — Collage Generation
- `mCreateCollage()` — PIL: side-by-side perk icons with title
- `mSaveImage()` — Save with auto-incrementing filename suffix

### `dbdwebscraper.py` — Wiki Scraper
- Fetches from `deadbydaylight.wiki.gg` API (MediaWiki parse endpoint)
- Parses survivor perk table → upserts into MySQL
- Downloads perk icons (high-res, removing `/thumb/` prefix)

---

## Config (`config/dbdconfig.json`)

```json
{
    "MAX_GENERATED_IMG_AGE": 3,
    "GENERATED_IMG_DIR": "assets/dbd/imgs/generated",
    "PERKS_IMG_DIR": "assets/dbd/imgs/perks",
    "PERKS_IMG_URL": "https://drive.google.com/file/d/...",
    "DBD_DB_UPDATE_MINS": 60,
    "OLLAMA_URL": "http://localhost:11434/api/generate",
    "OLLAMA_MODEL": "llama3"
}
```

---

## Key Dependencies

discord.py, PyMySQL, chromadb, sentence-transformers, rapidfuzz, jellyfish, python-Levenshtein, Pillow, beautifulsoup4, requests, gdown, aiohttp, cachetools, matplotlib, seaborn, scikit-learn, pandas, numpy, python-dotenv

---

## Known Quirks / Gotchas

1. **`buttons.py` has a bug**: `mRegisterLoss` is missing the `if not self.__pressed:` check (the `self.__pressed = True` is incorrectly indented under the wrong `if`).
2. **SQL injection risk**: Raw f-string SQL queries throughout `sql.py`. Only `mPrepareString()` (single-quote escaping) is used.
3. **Perk images are named by UUID** (e.g., `a-666-<hex>.png`), not perk name. Lookup goes through `SQLRetriever.mGetPerkByName()` to find the UUID.
4. **`requirements.txt` is UTF-16 encoded** and cannot be read by standard tools expecting UTF-8.
5. **Admin-only commands** are hardcoded to user ID `612432506813284373`.
6. **Worker creation is lazy**: a `DbdWorker` is created (with DB calls to load blacklist/weights) on first command interaction, then cached for 1 hour via TTLCache.
7. **Weights only persist when < 1.0**: The `mSaveWeights` method only stores decayed weights; absent = 1.0.
8. **RAG data is rebuilt daily**: `cleanup_dbd_rag_data` clears both `llm_perk.json` and ChromaDB, so next synergy call re-initializes everything.
