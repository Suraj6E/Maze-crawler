# Maze Crawler

An agent for the **[Maze Crawler Kaggle competition](https://www.kaggle.com/competitions/maze-crawler)**.

## How this project works

The game itself — the maze, the rules, the match runner, and the replay viewer —
all ship inside the **`kaggle-environments`** Python package, where Maze Crawler
is the **`crawl`** environment. You don't write any of that. **Your only job is to
write the agent** (the "brain") that, each turn, looks at what it can see and
decides what every robot should do.

```
            ┌─────────────────────────── you edit this ──────────────────────────┐
 main.py ──▶ agents/crawl-agent/main.py : agent(obs, config) ──▶ {robot_uid: "ACTION"}
    │                                                                      │
    │   feeds your agent + a 2nd agent into the `crawl` engine            │
    ▼                                                                      ▼
 kaggle-environments "crawl"  ── simulates the whole match ──▶  data/crawl_replay.html
                                                                  (open in a browser)
```

So the loop is: **edit your agent → run `main.py` → watch the replay → repeat.**

The game is a 1v1 race on a maze that scrolls north and deletes whatever falls off
the bottom. You build robots, gather energy, and try to outlast the opponent. Read
**[GAME_GUIDE.md](GAME_GUIDE.md)** for the full rules with diagrams.

## Project structure

| Path | What it is |
| ---- | ---------- |
| `main.py` | **Run the project.** Plays a match, writes + opens the HTML replay. |
| `agents/crawl-agent/main.py` | **Your agent — edit this.** The `agent(obs, config)` function. |
| `viewer.py` | Builds the standalone HTML replay viewer (theme + per-player views). |
| `GAME_GUIDE.md` | Rules, robot types, scoring, and diagrams. |
| `data/` | Replay output (`crawl_replay.html`). Git-ignored. |
| `.venv/` | Virtual environment with `kaggle-environments`. Git-ignored. |
| (rules) | `.venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md` — the official spec. |

## Setup (one time)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install kaggle-environments
```

(macOS/Linux: `python3 -m venv .venv && .venv/bin/pip install kaggle-environments`)

## Run it

Use the virtual environment's Python:

```powershell
.\.venv\Scripts\python main.py
```

That plays **your agent vs the built-in `random` agent**, prints the result, writes
`data/crawl_replay.html`, and **opens it in your browser** to watch. The replay is a
standalone file — no server needed.

Common variations:

```powershell
.\.venv\Scripts\python main.py --seed 7                       # different map
.\.venv\Scripts\python main.py --p2 agents/crawl-agent/main.py # vs a copy of yourself
.\.venv\Scripts\python main.py --no-open                      # don't auto-open the browser
.\.venv\Scripts\python main.py random random                  # two random agents
```

Tip: activate the venv once (`.\.venv\Scripts\Activate.ps1`) and you can just type
`python main.py`.

### Watching the replay
The generated `data/crawl_replay.html` is an interactive viewer (built by
`viewer.py`). It has the controls the bundled engine viewer lacks:

- **Theme** — toggle light / dark.
- **View: All / P1 / P2** — `All` shows the combined map; `P1`/`P2` show only what
  that player can see (its own fog of war), so you can inspect each side's
  perspective. Remembered things (walls, mines) stay; crystals, mining nodes, and
  enemy robots outside that player's vision are hidden.
- **Playback** — play/pause, step buttons, a scrubber, and speed; arrow keys and
  space work too.

> The polished viewer on the Kaggle competition site is Kaggle's *hosted* viewer
> for ranked episodes — it isn't part of the pip package, so this is a local
> equivalent with the same theme + per-player-view features.

### Reading the result
`main.py` prints each player's reward. Roughly: a surviving player's reward is its
total robot energy; an eliminated player gets a negative score; a tie is `0.5`.
Full scoring is in [GAME_GUIDE.md](GAME_GUIDE.md).

## Where to change your strategy

Everything lives in **[agents/crawl-agent/main.py](agents/crawl-agent/main.py)** —
the `agent(obs, config)` function. It runs once per turn and returns a dict mapping
each of your robot ids to an action string:

```python
def agent(obs, config):
    actions = {}
    for uid, data in obs["robots"].items():
        rtype, col, row, energy, owner, move_cd, jump_cd, build_cd = data
        if owner != obs["player"]:
            continue                      # skip the opponent's robots
        actions[uid] = "NORTH"            # <-- your decision goes here
    return actions
```

- `obs` is what you can see (fog of war): your robots, discovered walls, visible
  crystals/mines/nodes, the boundaries. See the field list in `GAME_GUIDE.md`.
- Actions are strings like `"NORTH"`, `"BUILD_SCOUT_NORTH"`, `"JUMP_NORTH"`,
  `"TRANSFORM"`, `"IDLE"` — full list in `GAME_GUIDE.md`.

The current agent is a deliberately minimal **survival baseline**: head north, and
have the factory `JUMP_NORTH` over walls so it doesn't get scrolled off the map.
It beats `random`, and it's the starting point for a real strategy (economy,
mining, walls, combat, pathfinding).

## Submitting to Kaggle

Maze Crawler is a **Simulations** competition: you submit the *agent*, and Kaggle
runs the same `crawl` environment on its servers, calling your `agent(obs, config)`
exactly like `main.py` does locally. Our agent is a single self-contained file
(`agents/crawl-agent/main.py`, no extra imports), so submitting is simple.

**Option A — Kaggle website (easiest):** on the competition's **Submit Agent**
page, upload `agents/crawl-agent/main.py` (or a `submission.tar.gz` with `main.py`
at its root). Kaggle validates it, then it plays ranked matches on the leaderboard.

**Option B — Kaggle API (command line):**

```powershell
# one-time: install the CLI and put your token at  ~/.kaggle/kaggle.json
.\.venv\Scripts\pip install kaggle

# package the agent (main.py must be at the root of the archive)
tar -czf submission.tar.gz -C agents/crawl-agent main.py

# submit
.\.venv\Scripts\kaggle competitions submit -c maze-crawler -f submission.tar.gz -m "baseline"
```

If your agent ever grows to multiple files, put them all in the same folder as
`main.py` and include them in the tarball (keep `main.py` at the root). Watch your
submitted games on the competition site using Kaggle's hosted viewer.

> Note: the exact submission UI/labels are on the competition page (which requires
> sign-in), so confirm there — but the agent format above is the standard for these
> `kaggle-environments` Simulations competitions.
