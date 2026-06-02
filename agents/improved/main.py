"""Improved Maze Crawler (`crawl`) agent: greedy economy + wall-aware movement
plus an endgame survival mode. agents/greedy/main.py is left untouched.

Robot type ids: 0=Factory, 1=Scout, 2=Worker, 3=Miner.  NORTH = increasing row.
Wall bitfield: N=1, E=2, S=4, W=8.
Full rules: .venv/Lib/site-packages/kaggle_environments/envs/crawl/README.md
"""

DIR_WALL_BIT = {"NORTH": 1, "EAST": 2, "SOUTH": 4, "WEST": 8}

ENDGAME_STEP = 440
SCOUT_CAP = 2
SAFE_NORTH_MARGIN = 4


def _parse(key):
    col, row = key.split(",")
    return int(col), int(row)


def _wall_bits(obs, config, col, row):
    """Discovered wall bitfield at (col,row); 0 when unknown or out of range."""
    walls = obs.get("walls") or []
    sb = obs.get("southBound", 0)
    idx = (row - sb) * config["width"] + col
    if 0 <= idx < len(walls):
        v = walls[idx]
        return v if v >= 0 else 0
    return 0


def _passable(obs, config, col, row, direction):
    """Whether stepping `direction` from (col,row) is open (known walls) and in bounds."""
    if _wall_bits(obs, config, col, row) & DIR_WALL_BIT[direction]:
        return False
    width = config["width"]
    if direction == "EAST":
        return col + 1 < width
    if direction == "WEST":
        return col - 1 >= 0
    if direction == "SOUTH":
        return row - 1 >= obs.get("southBound", 0)
    return True  # NORTH: always allowed, the map opens northward


def _toward(col, row, tcol, trow):
    """Direction preference list toward a target: bigger-gap axis first, NORTH last, never SOUTH."""
    dcol, drow = tcol - col, trow - row
    vert = "NORTH" if drow > 0 else ("SOUTH" if drow < 0 else None)
    horiz = "EAST" if dcol > 0 else ("WEST" if dcol < 0 else None)
    order = [vert, horiz] if abs(drow) >= abs(dcol) else [horiz, vert]
    prefs = [d for d in order if d and d != "SOUTH"]
    if "NORTH" not in prefs:
        prefs.append("NORTH")
    return prefs


def _nearest_north_of(targets, col, row):
    """Closest target (Manhattan) that is not south of (col,row), or None."""
    best, best_d = None, 1e9
    for key in targets:
        tcol, trow = _parse(key)
        if trow < row:
            continue
        d = abs(tcol - col) + abs(trow - row)
        if d < best_d:
            best, best_d = (tcol, trow), d
    return best


def _move_toward(obs, config, col, row, target):
    """First passable direction toward target (north-biased when target is None); NORTH if boxed in."""
    prefs = _toward(col, row, *target) if target else ["NORTH", "EAST", "WEST"]
    for d in prefs:
        if _passable(obs, config, col, row, d):
            return d
    return "NORTH"


def _open_build_dir(obs, config, col, row):
    """Adjacent open, in-bounds direction to spawn into (NORTH>EAST>WEST, never SOUTH); None if boxed."""
    bits = _wall_bits(obs, config, col, row)
    width = config["width"]
    north = obs.get("northBound", row)
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

    miner_cost = config["minerCost"]
    scout_cost = config["scoutCost"]
    south = obs.get("southBound", 0)
    endgame = step >= ENDGAME_STEP

    mine = [(uid, d) for uid, d in robots.items() if d[4] == player]
    have_miner = any(d[0] == 3 for _, d in mine)
    n_scouts = sum(1 for _, d in mine if d[0] == 1)

    for uid, d in mine:
        rtype, col, row, energy, owner, move_cd, jump_cd, build_cd = d

        if rtype == 0:  # Factory
            factory_safe = (row - south) >= SAFE_NORTH_MARGIN
            can_build = build_cd == 0 and not endgame
            build_dir = _open_build_dir(obs, config, col, row) if can_build else None

            if build_dir and not have_miner and nodes and factory_safe and energy >= miner_cost + 200:
                actions[uid] = f"BUILD_MINER_{build_dir}"
                have_miner = True
            elif build_dir and n_scouts < SCOUT_CAP and (factory_safe or step == 0) and energy >= scout_cost + 150:
                actions[uid] = f"BUILD_SCOUT_{build_dir}"
                n_scouts += 1
            elif jump_cd == 0:
                actions[uid] = "JUMP_NORTH"
            else:
                actions[uid] = _move_toward(obs, config, col, row, None)

        elif rtype == 3:  # Miner -> reach a node and turn into a mine
            if f"{col},{row}" in nodes:
                actions[uid] = "TRANSFORM"
            elif endgame:
                actions[uid] = _move_toward(obs, config, col, row, None)
            else:
                actions[uid] = _move_toward(obs, config, col, row, _nearest_north_of(nodes, col, row))

        else:  # Scout / Worker -> grab a crystal, else climb north
            if endgame:
                actions[uid] = _move_toward(obs, config, col, row, None)
            else:
                actions[uid] = _move_toward(obs, config, col, row, _nearest_north_of(crystals, col, row))

    return actions