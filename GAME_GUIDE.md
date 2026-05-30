# Maze Crawler (`crawl`) — Game Guide

A 1v1 strategy game on a **20-wide, infinitely north-scrolling maze** with fog of
war. You start with one **Factory** near the bottom. The southern edge keeps
advancing north and **destroys everything it passes**. The last player with a
living factory wins. Max 501 steps.

> Full spec: `.venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md`

## The big idea

```mermaid
flowchart TD
    subgraph MAZE["20-wide maze, mirrored left/right"]
        direction TB
        N["⬆ NORTH — map opens up here, go this way"]
        S["⬇ SOUTH boundary creeps up every few turns and DELETES everything below it"]
    end
    N -.survive by climbing north.-> S

    F["🏭 FACTORY (you start here)<br/>indestructible · unlimited energy<br/>if it falls below the south edge → YOU LOSE"]
    F --> N
```

The whole game is a race: **explore and grow faster than the scroll eats you**,
and don't let your factory get trapped behind walls.

## Robots & economy (the "tech tree")

Every robot burns **1 energy/turn**; at 0 energy it's forced idle. Energy comes
from **crystals** (one-time pickups) and **mines** (passive income you build).

```mermaid
flowchart LR
    F["🏭 Factory<br/>vision 4 · moves every 2 turns<br/>BUILD (10cd) · JUMP 2 cells over walls (20cd)"]

    F -- "50 energy" --> SC["🔭 Scout<br/>max E 100 · moves every turn<br/>vision 5 — fast explorer"]
    F -- "200 energy" --> WK["🔧 Worker<br/>max E 300 · vision 3<br/>BUILD/REMOVE walls (100 E)"]
    F -- "300 energy" --> MN["⛏ Miner<br/>max E 500 · vision 3<br/>TRANSFORM on a mining node"]

    MN -- "TRANSFORM (100 E)<br/>on a ⬡ mining node" --> MINE["💎 Mine<br/>+50 energy/turn, up to 1000<br/>friendly robots standing on it refuel"]

    CRY["✦ Crystals (scattered, 10–50 E)<br/>grabbed by moving onto them"] -.one-time.-> F
    MINE -.passive income.-> F
```

| Robot | Cost | Max E | Moves | Vision | Special |
|-------|-----:|------:|:-----:|:------:|---------|
| 🏭 Factory | — | ∞ | every 2 turns | 4 | BUILD, JUMP (over walls), **indestructible** |
| 🔭 Scout | 50 | 100 | every turn | 5 | fast exploration |
| 🔧 Worker | 200 | 300 | every 2 turns | 3 | build / remove walls |
| ⛏ Miner | 300 | 500 | every 2 turns | 3 | turn into a mine on a node |

## A turn, start to finish

```mermaid
flowchart TD
    A["1 · Cooldowns tick"] --> B["2 · Validate actions"]
    B --> C["3 · Every robot −1 energy"]
    C --> D["4 · Special actions<br/>TRANSFORM · build/remove walls · build robots · transfer"]
    D --> E["5 · Movement + combat<br/>(see crush rules)"]
    E --> F2["6 · Collect crystals"]
    F2 --> G["7–8 · Mines refuel robots & gain +50"]
    G --> H["9 · SCROLL: south edge advances, new row appears"]
    H --> I["10 · Destroy everything below the south edge"]
    I --> J{"11 · A factory gone?"}
    J -- yes --> WIN["Win / lose / tiebreak"]
    J -- no --> K["12 · Recompute fog of war"]
    K --> A
```

**Combat (crush rules)** when robots share a cell — *ownership doesn't matter,
friendly fire is real*: **Factory > Miner > Worker > Scout**; stronger crushes
weaker; **same type ⇒ all destroyed**. Factory is indestructible to non-factories.

## How the scroll speeds up

```mermaid
flowchart LR
    S0["Steps 0–~450<br/>scroll every 10 turns<br/>(slow, ramping up)"] --> S1["Steps 450–500<br/>scroll every 2 turns<br/>(brutal, fast)"] --> END["Step 500<br/>game ends → tiebreak"]
```

## Winning

```mermaid
flowchart TD
    START{"How does it end?"}
    START -- "one factory destroyed" --> W1["Other player WINS"]
    START -- "both factories alive at step 500<br/>OR both die same turn" --> TB["Tiebreaker cascade"]
    TB --> T1{"More total energy?"}
    T1 -- yes --> WIN["higher → win"]
    T1 -- "tie" --> T2{"More robots?"}
    T2 -- yes --> WIN
    T2 -- "tie" --> DRAW["true draw — both get 0.5"]
```

**Reward** (what `main.py` prints): alive → your total robot energy; win by
tiebreak → `1`; loss → `0`; draw → `0.5`; eliminated → a negative number (the
earlier you die, the more negative).

## What your agent sees & does

```python
def agent(obs, config):
    obs["player"]   # 0 or 1 — which side you are
    obs["step"]     # current turn
    obs["robots"]   # {uid: [type, col, row, energy, owner, move_cd, jump_cd, build_cd]}
    obs["walls"]    # discovered maze layout (bitfield: N=1 E=2 S=4 W=8; -1 = unknown)
    obs["crystals"] # {"col,row": energy}   (only what's currently in view)
    obs["mines"]    # {"col,row": [energy, max, owner]}  (remembered once seen)
    obs["miningNodes"]  # {"col,row": 1}    (only currently in view)
    obs["southBound"], obs["northBound"]    # the deadly edge + the top
    # return: {uid: "ACTION"} e.g. "NORTH", "BUILD_SCOUT_NORTH", "JUMP_NORTH", "TRANSFORM", "IDLE"
```

Fog of war: you only see within your robots' combined vision. Walls and mines are
*remembered*; crystals, enemies, and mining nodes are **not** — they vanish from
your view once no robot can see them.

The current baseline in [agents/crawl-agent/main.py](agents/crawl-agent/main.py)
does the minimum to survive: head north, and have the factory `JUMP_NORTH` over
walls so it doesn't get scrolled off. Everything else (economy, mining, walls,
combat, pathfinding) is yours to build.
