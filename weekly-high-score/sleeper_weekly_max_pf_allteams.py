
import sys
import time
import json
from collections import defaultdict
from typing import Dict, List, Tuple
import requests

BASE_URL = "https://api.sleeper.app/v1"

# Fixed lineup (no FLEX) per user requirements:
FIXED_REQUIRED = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DEF": 1, "K": 1}
# Normalize possible aliases from Sleeper/player DBs:
POS_ALIAS = {"DST": "DEF", "D/ST": "DEF", "PK": "K"}

def normalize_pos(pos: str) -> str:
    return POS_ALIAS.get(pos, pos)

def get_json(url: str, retries: int = 3, sleep_s: float = 0.6):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(sleep_s)
    raise RuntimeError(f"GET failed for {url}: {last}")

def get_league(league_id: str) -> dict:
    return get_json(f"{BASE_URL}/league/{league_id}")

def get_users(league_id: str) -> List[dict]:
    return get_json(f"{BASE_URL}/league/{league_id}/users")

def get_rosters(league_id: str) -> List[dict]:
    return get_json(f"{BASE_URL}/league/{league_id}/rosters")

def get_matchups(league_id: str, week: int) -> List[dict]:
    return get_json(f"{BASE_URL}/league/{league_id}/matchups/{week}")

def get_players() -> Dict[str, dict]:
    # Big payload (few MB). Cache if you'd like.
    return get_json(f"{BASE_URL}/players/nfl")

def owner_name_lookup(users: List[dict]) -> Dict[str, str]:
    """Map user_id -> best display string (team_name if present, else display_name/username)."""
    out = {}
    for u in users:
        uid = u.get("user_id")
        meta = u.get("metadata") or {}
        team_name = meta.get("team_name") or ""
        display = u.get("display_name") or u.get("username") or uid
        out[uid] = team_name if team_name else display
    return out

def roster_owner_lookup(rosters: List[dict]) -> Dict[int, str]:
    """Map roster_id -> owner_id (primary)."""
    out = {}
    for r in rosters:
        rid = r.get("roster_id")
        owner = r.get("owner_id") or ""
        out[rid] = owner
    return out

def compute_required_from_league(league: dict) -> Dict[str, int]:
    """
    Build required counts from league.roster_positions, but ignore BN/IR/TAXI and any FLEX-like slots,
    then overlay with fixed required to ensure the league is consistent with the user's format.
    """
    rp = league.get("roster_positions") or []
    counts = defaultdict(int)
    ignore = {"BN", "IR", "TAXI"}
    # allowed fixed slots only:
    allowed = set(FIXED_REQUIRED.keys())
    for pos in rp:
        if pos in ignore:
            continue
        p = normalize_pos(pos)
        if p in allowed:
            counts[p] += 1
    # If league data doesn't specify, fallback to the fixed required counts
    for k, v in FIXED_REQUIRED.items():
        if counts.get(k, 0) == 0:
            counts[k] = v
    return dict(counts)

def build_player_meta_by_id(players_all: dict) -> Dict[str, dict]:
    """
    Extract id -> {'full_name':..., 'position':...}
    Sleeper keys are strings (player_id). Position is like 'QB','RB','WR','TE','DEF','K'.
    """
    out = {}
    for pid, meta in players_all.items():
        full = meta.get("full_name") or " ".join([meta.get("first_name",""), meta.get("last_name","")]).strip() or pid
        pos = normalize_pos(meta.get("position") or "")
        out[pid] = {"full_name": full, "position": pos}
    return out

def build_roster_pool(matchup_entry: dict, player_meta_by_id: Dict[str,dict]) -> List[dict]:
    """
    From the matchup entry for THIS roster, build a pool of all rostered players and their week points.
    We take `players` (starters + bench + IR/taxi on roster that week) and `players_points` for scores.
    """
    pids = matchup_entry.get("players") or []
    points_map = matchup_entry.get("players_points") or {}
    out = []
    for pid in pids:
        meta = player_meta_by_id.get(pid, {})
        pos = normalize_pos(meta.get("position") or "")
        score = float(points_map.get(pid, 0.0) or 0.0)
        out.append({
            "player_id": pid,
            "player_name": meta.get("full_name") or pid,
            "position": pos,
            "score": score,
        })
    return out

def select_fixed_best(players: List[dict], required: Dict[str,int]) -> Tuple[List[dict], float]:
    """
    For fixed slots (no flex), this is optimal: pick top-N by score per position.
    If not enough players at a position, take what exists.
    """
    by_pos = defaultdict(list)
    for p in players:
        if p["position"] in required:
            by_pos[p["position"]].append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x["score"], reverse=True)

    chosen = []
    for pos, need in required.items():
        chosen += [{**p, "slot": pos} for p in by_pos.get(pos, [])[:need]]
    total = sum(p["score"] for p in chosen)
    return chosen, total

def find_top_roster_for_week(league_id: str, week: int):
    league = get_league(league_id)
    required = compute_required_from_league(league)
    users = get_users(league_id)
    rosters = get_rosters(league_id)
    matchups = get_matchups(league_id, week)
    players_all = get_players()

    name_by_user = owner_name_lookup(users)
    owner_by_roster = roster_owner_lookup(rosters)

    # index matchup entry by roster_id
    matchup_by_rid = {}
    for m in matchups:
        rid = m.get("roster_id")
        if rid is not None:
            matchup_by_rid[rid] = m

    meta_by_id = build_player_meta_by_id(players_all)

    best = {
        "roster_id": None,
        "owner_name": "",
        "total": -1.0,
        "lineup": [],
    }

    results = []  # keep all for optional inspection

    for rid, owner_id in owner_by_roster.items():
        m = matchup_by_rid.get(rid)
        if not m:
            # no matchup entry (bye or league oddity) — skip
            continue
        pool = build_roster_pool(m, meta_by_id)
        lineup, total = select_fixed_best(pool, required)
        owner_name = name_by_user.get(owner_id, f"Roster {rid}")
        results.append({"roster_id": rid, "owner_name": owner_name, "total": total, "lineup": lineup})
        if total > best["total"]:
            best.update({"roster_id": rid, "owner_name": owner_name, "total": total, "lineup": lineup})

    return best, results, required

def print_winner(best: dict, required: Dict[str,int], league_id: str, week: int):
    print(f"\nLeague {league_id} — Week {week}")
    print("Fixed-slot requirements (no FLEX): " + ", ".join(f"{k}={v}" for k,v in required.items()))
    print(f"\nTop roster: {best['owner_name']} (roster_id={best['roster_id']})")
    print(f"Max possible points: {best['total']:.2f}\n")
    # sort by slot order for stable print
    slot_order = list(required.keys())
    lineup_sorted = sorted(best["lineup"], key=lambda p: slot_order.index(p["slot"]) if p["slot"] in slot_order else 999)
    for p in lineup_sorted:
        print(f"  {p['slot']:>3}  {p['player_name']:<28} {p['score']:.2f}")


def print_all(results: list, required: Dict[str,int], league_id: str, week: int):
    print(f"\nLeague {league_id} — Week {week}")
    print("Fixed-slot requirements (no FLEX): " + ", ".join(f"{k}={v}" for k,v in required.items()))
    print("\n=== All Teams (sorted by max possible points) ===")
    # stable slot ordering
    slot_order = list(required.keys())
    # sort teams by total desc, then by name
    results_sorted = sorted(results, key=lambda r: (-r["total"], r["owner_name"]))
    for rank, r in enumerate(results_sorted, 1):
        print(f"\n[{rank}] {r['owner_name']} (roster_id={r['roster_id']}) — {r['total']:.2f}")
        lineup_sorted = sorted(r["lineup"], key=lambda p: slot_order.index(p["slot"]) if p["slot"] in slot_order else 999)
        for p in lineup_sorted:
            print(f"  {p['slot']:>3}  {p['player_name']:<28} {p['score']:.2f}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python sleeper_weekly_max_pf.py <LEAGUE_ID> <WEEK>")
        sys.exit(2)
    league_id = sys.argv[1]
    try:
        week = int(sys.argv[2])
    except:
        print("WEEK must be an integer.")
        sys.exit(2)

    best, all_results, required = find_top_roster_for_week(league_id, week)
    if best["roster_id"] is None:
        print("No valid matchups found for that week.")
        sys.exit(1)
    print_winner(best, required, league_id, week)
    print_all(all_results, required, league_id, week)

if __name__ == "__main__":
    main()
