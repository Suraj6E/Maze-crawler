# Maze Crawler

A workspace for building an agent for the **[Maze Crawler Kaggle competition](https://www.kaggle.com/competitions/maze-crawler)**.

The game runs on Kaggle's `kaggle-environments` package, where it is the **`crawl`**
environment ("Crawl"): *a maze-crawling strategy game with fog of war — two players
navigate an infinite northward-scrolling maze, building robots to explore, collect
energy, and outlast the opponent.*

> The engine and rules ship inside `kaggle-environments`; you only write the agent
> (the brain). See [GAME_GUIDE.md](GAME_GUIDE.md) for a diagram and rules summary.

## What is what

| Path | What it is |
| ---- | ---------- |
| `agents/crawl-agent/main.py` | **Your** agent. Implement the `agent(obs, config)` function here. |
| `scripts/run_crawl.py` | Runs a match and writes a self-contained HTML replay. |
| `run.ps1` | Convenience wrapper around `run_crawl.py`. |
| `data/` | Replay output (git-ignored). |
| `.venv/` | Virtual environment with `kaggle-environments` installed (git-ignored). |
| official rules | `.venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md` |

## Setup (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install kaggle-environments
```

## Run a match — with visuals

```powershell
.\run.ps1                 # crawl-agent vs the built-in "random" agent
.\run.ps1 -Open           # ...and open the replay in your browser automatically
.\run.ps1 -P2 agents/crawl-agent -Seed 7   # vs a copy of your own agent
```

This writes `data/crawl_replay.html` and prints the result. The replay is a
**standalone HTML file** — just double-click it (or use `-Open`) to watch in any
browser. No dev server needed.

Direct equivalent without the wrapper:

```powershell
.\.venv\Scripts\python scripts\run_crawl.py agents/crawl-agent/main.py random --seed 42
```

### Reward / scoring
`run.ps1` prints each player's reward. Roughly: a surviving player's reward is its
total robot energy; eliminated players get a negative score; a tie gives `0.5`.
Full rules in [GAME_GUIDE.md](GAME_GUIDE.md).

## The dev loop

1. Edit your strategy in `agents/crawl-agent/main.py`
2. Re-run `.\run.ps1 -Open`
3. Watch the new replay — repeat
