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

Upload `agents/crawl-agent/main.py` as your submission — Kaggle runs the same
`crawl` environment on its servers, calling your `agent` function the same way
`main.py` does locally.
