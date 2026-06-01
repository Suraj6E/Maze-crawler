"""Greedy Maze Crawler agent — survival + a simple economy.

A step up from the `baseline` (which only survives). This one tries to actually
*score* by growing energy:

  - Factory: survive first (head north, JUMP_NORTH over walls). Occasionally
    spends a turn to build — a Miner if it doesn't have one yet (passive mine
    income), otherwise Scouts (cheap vision + crystal grabbers). It builds toward
    whichever adjacent direction is actually open (not into a wall, never south).
  - Miners: walk to the nearest visible mining node and TRANSFORM into a mine
    (+50 energy/turn for friendly robots on it).
  - Scouts / Workers: walk to the nearest visible crystal, else explore north.

Safety rule: the maze scrolls north and the south edge kills anything it passes,
so units never chase a target that is *south* of them. Pathing is intentionally
naive (greedy step toward the target; a wall just stalls the move) — improving it
is a good next exercise.

Robot type ids: 0=Factory, 1=Scout, 2=Worker, 3=Miner.  NORTH = increasing row.
Wall bitfield: N=1, E=2, S=4, W=8.
Full rules: .venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md
"""

DIR_WALL_BIT = {"NORTH": 1, "EAST": 2, "SOUTH": 4, "WEST": 8}


def _parse(key):
    col, row = key.split(",")
    return int(col), int(row)


def _step_toward(col, row, tcol, trow):
    """Greedy one-cell step toward (tcol,trow); prefers the larger-gap axis."""
    dcol, drow = tcol - col, trow - row
    if abs(drow) >= abs(dcol):
        if drow > 0:
            return "NORTH"
        if drow < 0:
            return "SOUTH"
    if dcol > 0:
        return "EAST"
    if dcol < 0:
        return "WEST"
    return "NORTH"


def _nearest_north_of(targets, col, row):
    """Closest target (Manhattan) that is not south of (col,row), or None."""
    best, best_d = None, 1e9
    for key in targets:
        tcol, trow = _parse(key)
        if trow < row:                  # south of us -> ignore (scroll death)
            continue
        d = abs(tcol - col) + abs(trow - row)
        if d < best_d:
            best, best_d = (tcol, trow), d
    return best


def _wall_bits(obs, config, col, row):
    """Wall bitfield at (col,row) from the fog-of-war wall array (0 if unknown)."""
    walls = obs.get("walls") or []
    sb = obs.get("southBound", 0)
    idx = (row - sb) * config["width"] + col
    if 0 <= idx < len(walls):
        v = walls[idx]
        return v if v >= 0 else 0
    return 0


def _open_build_dir(obs, config, col, row):
    """Pick an adjacent direction to spawn into that has no wall and is in-bounds.
    Prefer NORTH, then EAST, then WEST; never SOUTH (toward the scroll). None if
    fully boxed in."""
    bits = _wall_bits(obs, config, col, row)
    north = obs.get("northBound", row)
    width = config["width"]
    if not (bits & DIR_WALL_BIT["NORTH"]) and row + 1 <= north:
        return "NORTH"
    if not (bits & DIR_WALL_BIT["EAST"]) and col + 1 < width:
        return "EAST"
    if not (bits & DIR_WALL_BIT["WEST"]) and col - 1 >= 0:
        return "WEST"
    return None


def agent(obs, config):
    actions = {}
    player = obs["player"]
    step = obs["step"]
    robots = obs["robots"]
    crystals = obs.get("crystals", {}) or {}
    nodes = obs.get("miningNodes", {}) or {}

    mine_cost = config["minerCost"]
    scout_cost = config["scoutCost"]

    mine = [(uid, d) for uid, d in robots.items() if d[4] == player]
    have_miner = any(d[0] == 3 for _, d in mine)

    for uid, d in mine:
        rtype, col, row, energy, owner, move_cd, jump_cd, build_cd = d

        if rtype == 0:  # Factory
            # SURVIVAL FIRST: keep moving north or the scroll eats the factory.
            # Only sacrifice a movement turn to build now and then (~1 in 8), and
            # build into an OPEN direction so the attempt actually succeeds.
            build_dir = _open_build_dir(obs, config, col, row) if (build_cd == 0 and step % 8 == 0) else None
            if build_dir and not have_miner and energy >= mine_cost + 200:
                actions[uid] = f"BUILD_MINER_{build_dir}"
                have_miner = True
            elif build_dir and energy >= scout_cost + 150:
                actions[uid] = f"BUILD_SCOUT_{build_dir}"
            elif jump_cd == 0:
                actions[uid] = "JUMP_NORTH"     # bust through walls, outrun the scroll
            else:
                actions[uid] = "NORTH"

        elif rtype == 3:  # Miner -> reach a node and turn into a mine
            if f"{col},{row}" in nodes:
                actions[uid] = "TRANSFORM"
            else:
                tgt = _nearest_north_of(nodes, col, row)
                actions[uid] = _step_toward(col, row, *tgt) if tgt else "NORTH"

        else:  # Scout / Worker -> grab a crystal, else explore north
            tgt = _nearest_north_of(crystals, col, row)
            actions[uid] = _step_toward(col, row, *tgt) if tgt else "NORTH"

    return actions
