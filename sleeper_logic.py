import requests
import json
import os

BASE_URL = "https://api.sleeper.app/v1"

def get_user_id(username):
    response = requests.get(f"{BASE_URL}/user/{username}")
    data = response.json()
    if data is not None:
        return data.get("user_id")
    return None

def get_leagues(user_id, sport="nba", season="2026"): 
    response = requests.get(f"{BASE_URL}/user/{user_id}/leagues/{sport}/{season}")
    return response.json()

def get_rosters(league_id):
    response = requests.get(f"{BASE_URL}/league/{league_id}/rosters")
    return response.json()

def get_league_users(league_id):
    response = requests.get(f"{BASE_URL}/league/{league_id}/users")
    return response.json()

def get_traded_picks(league_id):
    response = requests.get(f"{BASE_URL}/league/{league_id}/traded_picks")
    return response.json()

def get_draft_data(league_id):
    response = requests.get(f"{BASE_URL}/league/{league_id}/drafts")
    drafts = response.json()
    if drafts and len(drafts) > 0:
        return drafts[0]
    return None

def fetch_all_players():
    if not os.path.exists("players.json"):
        print("Fetching global player data...")
        response = requests.get(f"{BASE_URL}/players/nba")
        with open("players.json", "w") as f:
            json.dump(response.json(), f)
    
    with open("players.json", "r") as f:
        return json.load(f)

def get_mapped_rosters(league_id, players_dict):
    rosters = get_rosters(league_id)
    traded_picks = get_traded_picks(league_id)
    draft = get_draft_data(league_id)
    
    roster_to_slot = {}
    if draft:
        slot_to_roster_id = draft.get("slot_to_roster_id")
        draft_order = draft.get("draft_order")
        
        if slot_to_roster_id:
            for slot_str, r_id in slot_to_roster_id.items():
                roster_to_slot[r_id] = int(slot_str)
        elif draft_order:
            for r in rosters:
                u_id = str(r.get("owner_id"))
                if u_id in draft_order:
                    roster_to_slot[r["roster_id"]] = draft_order[u_id]

    pick_inventory = []
    target_seasons = ["2026", "2027", "2028"]
    
    for r in rosters:
        rid = r["roster_id"]
        for season in target_seasons:
            # 🚨 UPDATED: Loop capped at 8 rounds
            for round_num in range(1, 9):
                traded_pick = next((p for p in traded_picks if p["roster_id"] == rid and p["round"] == round_num and p.get("season") == season), None)
                current_owner = traded_pick["owner_id"] if traded_pick else rid
                
                pick_slot = roster_to_slot.get(rid) if season == "2026" else None
                
                pick_inventory.append({
                    "season": season,
                    "round": round_num, 
                    "original_roster": rid, 
                    "current_owner": current_owner,
                    "pick_slot": pick_slot
                })

    for roster in rosters:
        player_names = []
        for p_id in roster.get("players", []):
            p_data = players_dict.get(p_id, {})
            name = f"{p_data.get('first_name')} {p_data.get('last_name')}"
            player_names.append({"id": p_id, "name": name, "age": p_data.get("age")})
        roster["player_details"] = player_names
        roster["draft_picks"] = [p for p in pick_inventory if p["current_owner"] == roster["roster_id"]]
        
    return rosters