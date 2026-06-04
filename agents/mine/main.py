

from collections import deque

DIR_WALL_BIT = {"NORTH": 1, "EAST": 2, "SOUTH": 4, "WEST": 8}

# Strategy Constants
ENDGAME_STEP = 440
NODE_MARGIN = 5      # Don't build mines too close to the scrolling edge
SAFE_MARGIN = 2      # Minimum distance units should keep from the southBound
SCOUT_CAP = 3        # Maximum number of scouts to maintain

def _parse(key):
    col, row = key.split(",")
    return int(col), int(row)


def _bfs_step(obs, config, scol, srow, tcol, trow):
    """Find the first move of the shortest path to (tcol, trow) using BFS."""
    if (scol, srow) == (tcol, trow):
        return "IDLE"

    width = config["width"]
    sb = obs.get("southBound", 0)
    # Search queue stores: (current_col, current_row, first_move_taken)
    queue = deque([(scol, srow, None)])
    visited = {(scol, srow)}
    
    iterations = 0
    while queue and iterations < 400:  # Safety cap for performance
        iterations += 1
        c, r, first = queue.popleft()
        
        if (c, r) == (tcol, trow):
            return first if first else "NORTH"

        bits = _wall_bits(obs, config, c, r)
        for move, dc, dr, bit in [("NORTH", 0, 1, 1), ("EAST", 1, 0, 2), 
                                  ("SOUTH", 0, -1, 4), ("WEST", -1, 0, 8)]:
            nc, nr = c + dc, r + dr
            
            # Basic bounds and wall collision check
            if not (0 <= nc < width and nr >= sb): continue
            if bits & bit: continue
            
            if (nc, nr) not in visited:
                visited.add((nc, nr))
                # Track the very first move made from the start point
                queue.append((nc, nr, move if first is None else first))

    return "NORTH"


def _nearest_north_of(targets, col, row, south, min_margin=0):
    """Closest target (Manhattan) not south of us and safely above southBound."""
    best, best_d = None, 1e9
    for key in targets:
        tcol, trow = _parse(key)
        if trow < row: continue
        if trow - south < min_margin: continue
        d = abs(tcol - col) + abs(trow - row)
        if d < best_d:
            best, best_d = (tcol, trow), d
    return best


def _nearest_friendly_mine(obs, player, col, row):
    """Finds the nearest friendly mine and its Manhattan distance."""
    best_mine_pos = None
    min_dist = float('inf')
    mines = obs.get("mines", {})
    for key, mine_data in mines.items():
        mine_owner = mine_data[2]
        if mine_owner == player:
            mcol, mrow = _parse(key)
            dist = abs(mcol - col) + abs(mrow - row)
            if dist < min_dist:
                min_dist = dist
                best_mine_pos = (mcol, mrow)
    return best_mine_pos, min_dist


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
    crystals = dict(obs.get("crystals", {}) or {}) # Local copy for claiming
    nodes = obs.get("miningNodes", {}) or {}
    south = obs.get("southBound", 0)
    endgame = step >= ENDGAME_STEP

    mine_cost = config["minerCost"]
    scout_cost = config["scoutCost"]

    my_units = [(uid, d) for uid, d in robots.items() if d[4] == player]
    factory_pos = next(((d[1], d[2]) for _, d in my_units if d[0] == 0), None)
    n_miners = sum(1 for _, d in my_units if d[0] == 3)
    n_scouts = sum(1 for _, d in my_units if d[0] == 1)
    
    # Nodes far enough north to justify investment
    viable_nodes = [k for k in nodes if _parse(k)[1] - south >= NODE_MARGIN]

    for uid, d in my_units:
        rtype, col, row, energy, owner, move_cd, jump_cd, build_cd = d

        # 0. Emergency Safety Override
        if rtype != 0 and (row - south) < SAFE_MARGIN:
            actions[uid] = "NORTH"
            continue

        if rtype == 0:  # Factory
            factory_safe = (row - south) >= 6
            # Don't build if we need to jump or if it's endgame
            can_build = not endgame and build_cd == 0 and jump_cd > 0 and factory_safe
            
            build_dir = _open_build_dir(obs, config, col, row) if (can_build and step % 4 == 0) else None
            
            if build_dir and n_miners < len(viable_nodes) and energy >= mine_cost + 300:
                actions[uid] = f"BUILD_MINER_{build_dir}"
                n_miners += 1
            elif build_dir and n_scouts < SCOUT_CAP and energy >= scout_cost + 150:
                actions[uid] = f"BUILD_SCOUT_{build_dir}"
                n_scouts += 1
            elif jump_cd == 0:
                actions[uid] = "JUMP_NORTH"     # bust through walls, outrun the scroll
            else:
                actions[uid] = "NORTH"

        elif rtype == 3:  # Miner -> reach a node and turn into a mine
            # Transform if we are on a node and have enough energy (costs 100)
            if f"{col},{row}" in nodes and energy >= 100:
                actions[uid] = "TRANSFORM"
            # Refuel logic: prioritize nearest friendly mine, then factory
            elif energy < 125: # Low energy threshold
                target_refuel_pos = None
                
                nearest_mine_pos, mine_dist = _nearest_friendly_mine(obs, player, col, row)
                
                factory_dist = float('inf')
                if factory_pos:
                    factory_dist = abs(factory_pos[0] - col) + abs(factory_pos[1] - row)
                
                if nearest_mine_pos and mine_dist < factory_dist:
                    target_refuel_pos = nearest_mine_pos
                elif factory_pos:
                    target_refuel_pos = factory_pos
                
                if target_refuel_pos:
                    actions[uid] = _bfs_step(obs, config, col, row, *target_refuel_pos)
                else:
                actions[uid] = _bfs_step(obs, config, col, row, *factory_pos)
            elif endgame:
                actions[uid] = _bfs_step(obs, config, col, row, col, row + 10)
            else:
                tgt = _nearest_north_of(nodes, col, row, south, min_margin=2)
                actions[uid] = _bfs_step(obs, config, col, row, *tgt) if tgt else "NORTH"

        else:  # Scout / Worker
            if endgame:
                actions[uid] = _bfs_step(obs, config, col, row, col, row + 10)
            else:
                tgt = _nearest_north_of(crystals, col, row, south, min_margin=0)
                if tgt: # Claim crystal so others don't chase it
                    crystals.pop(f"{tgt[0]},{tgt[1]}", None)
                    actions[uid] = _bfs_step(obs, config, col, row, *tgt)
                else:
                    actions[uid] = "NORTH"

    return actions
