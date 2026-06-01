"""Basic Maze Crawler (`crawl`) agent — a survival baseline (no real strategy).

The maze scrolls NORTH; the south boundary destroys anything it passes. So the
one thing that matters for a baseline is: keep heading north, and don't let the
factory get walled in and left behind.

  - Factory: JUMP_NORTH when the jump is off cooldown (leaps 2 cells, ignoring
    walls — this is what stops it getting stuck behind a wall and scrolled off);
    otherwise plain NORTH. Builds one Scout on the very first turn for vision.
  - All other robots: head NORTH.

This is deliberately minimal. Building an economy (workers, miners, mines),
fighting, and pathfinding are left for a real strategy later.

Robot type ids: 0=Factory, 1=Scout, 2=Worker, 3=Miner
Full rules: .venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md
"""


def agent(obs, config):
    actions = {}
    step = obs["step"]

    for uid, data in obs["robots"].items():
        rtype, col, row, energy, owner, move_cd, jump_cd, build_cd = data
        if owner != obs["player"]:
            continue

        if rtype == 0:  # Factory
            if step == 0 and build_cd == 0:
                actions[uid] = "BUILD_SCOUT_NORTH"   # one scout for early vision
            elif jump_cd == 0:
                actions[uid] = "JUMP_NORTH"           # bust through walls, stay ahead of scroll
            else:
                actions[uid] = "NORTH"
        else:  # Scout / Worker / Miner
            actions[uid] = "NORTH"

    return actions
