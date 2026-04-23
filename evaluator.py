import pandas as pd
import itertools
import scraper
from utils import clean_name

def apply_keeper_premium(live_values, top_n=24, premium=1.15):
    """Applies a 15% value bump to the Top 24 players in the global market to account for absolute scarcity."""
    sorted_items = sorted(live_values.items(), key=lambda x: x[1], reverse=True)
    adjusted_values = {}
    for i, (player, val) in enumerate(sorted_items):
        if i < top_n:
            adjusted_values[player] = val * premium
        else:
            adjusted_values[player] = val
    return adjusted_values

def get_team_valuation(roster):
    """Sorts roster into Keepers, Rentals, and Draft Picks."""
    player_details = roster["player_details"]
    draft_picks = roster.get("draft_picks", [])
    raw_values = scraper.get_player_value_dict()
    
    # Apply the 15% bump to the Top 24 assets
    live_values = apply_keeper_premium(raw_values, top_n=24, premium=1.15)
    
    for p in player_details:
        p_name_clean = clean_name(p["name"])
        p["market_value"] = int(live_values.get(p_name_clean, 500))
        
    sorted_p = sorted(player_details, key=lambda x: x["market_value"], reverse=True)
    
    # Specific Draft Pick Valuation (Sliding Scale)
    base_pick_values = {1: 1200, 2: 800, 3: 500}
    evaluated_picks = []
    
    for p in draft_picks:
        rnd = p['round']
        slot = p.get('pick_slot')
        
        if slot:
            # Sliding scale based on an 8-team league median (4.5)
            multiplier = {1: 100, 2: 50, 3: 25}.get(rnd, 0)
            slot_adjust = (4.5 - slot) * multiplier 
            val = base_pick_values.get(rnd, 200) + slot_adjust
            name = f"Round {rnd} (Pick {slot})"
        else:
            val = base_pick_values.get(rnd, 200)
            name = f"Round {rnd} Pick"
            
        evaluated_picks.append({
            "name": name,
            "market_value": int(val)
        })

    return {
        "keepers": sorted_p[:3],
        "keeper_score": sum(p["market_value"] for p in sorted_p[:3]),
        "surplus_keeper": sorted_p[3] if len(sorted_p) > 3 else None,
        "rentals": sorted_p[3:],
        "picks": sorted(evaluated_picks, key=lambda x: x["market_value"], reverse=True)
    }

def generate_trade_packages(my_eval, their_eval):
    """Dynamically generates 2-for-1, 3-for-2, and Pick-Swap combinations."""
    packages = []
    
    my_pool = my_eval["rentals"][:4] + my_eval.get("picks", [])
    their_pool = their_eval["keepers"] + their_eval["rentals"][:2] + their_eval.get("picks", [])

    for my_len in [1, 2, 3]:
        for their_len in [1, 2]:
            for my_combo in itertools.combinations(my_pool, my_len):
                for their_combo in itertools.combinations(their_pool, their_len):
                    
                    my_players = [i for i in my_combo if "Round" not in i["name"]]
                    their_players = [i for i in their_combo if "Round" not in i["name"]]
                    
                    net_roster_spots = len(my_players) - len(their_players)
                    if net_roster_spots < 0:
                        continue
                        
                    my_raw_val = sum(i["market_value"] for i in my_combo)
                    their_raw_val = sum(i["market_value"] for i in their_combo)
                    
                    # The 25% extra-player tax
                    tax_rate = 0.25 if net_roster_spots == 1 else (0.35 if net_roster_spots == 2 else 0.0)
                    my_effective_val = my_raw_val * (1 - tax_rate)
                    
                    my_best_item = max((i["market_value"] for i in my_combo), default=0)
                    their_best_item = max((i["market_value"] for i in their_combo), default=0)
                    
                    if their_raw_val * 0.90 <= my_effective_val <= their_raw_val * 1.15:
                        if my_best_item >= their_best_item * 0.65:
                            
                            offer_str = " + ".join([f"{i['name']} ({i['market_value']})" for i in my_combo])
                            receive_str = " + ".join([f"{i['name']} ({i['market_value']})" for i in their_combo])
                            
                            if net_roster_spots == 1 and my_len == 2: t_type = "2-for-1 Consolidation"
                            elif net_roster_spots == 2 and my_len == 3: t_type = "3-for-1 Blockbuster"
                            elif my_len == 3 and their_len == 2: t_type = "3-for-2 Package"
                            elif "Round" in offer_str and net_roster_spots == 0: t_type = "Player + Pick Swap"
                            else: t_type = "Structured Package"

                            packages.append({
                                "offer": offer_str,
                                "receive": receive_str,
                                "value_diff": abs(my_effective_val - their_raw_val),
                                "label": t_type,
                                "tax": tax_rate
                            })
                            
    packages.sort(key=lambda x: x["value_diff"])
    unique_packages = []
    seen = set()
    for p in packages:
        trade_hash = p["offer"] + "|" + p["receive"]
        if trade_hash not in seen:
            seen.add(trade_hash)
            unique_packages.append(p)
            if len(unique_packages) >= 2: 
                break
                
    return unique_packages

# 🚨 ADDED league_users to the function arguments
def find_vibe_trades(my_roster, other_rosters, my_user_id, league_users):
    my_eval = get_team_valuation(my_roster)
    recommendations = []

    for team in other_rosters:
        if team["owner_id"] == my_user_id: 
            continue
        
        their_eval = get_team_valuation(team)
        
        # 🚨 NEW: Map the owner_id to their custom team name
        owner_id_str = str(team.get("owner_id"))
        user_info = next((u for u in league_users if str(u.get("user_id")) == owner_id_str), None)
        
        if user_info:
            team_name = user_info.get("metadata", {}).get("team_name")
            target_team_name = team_name if team_name else user_info.get("display_name")
        else:
            target_team_name = f"Team {team['roster_id']}"
        
        if my_eval["surplus_keeper"] and my_eval["surplus_keeper"]["market_value"] > 1500:
            if their_eval["keepers"][2]["market_value"] < 1200:
                r1_pick = next((p for p in their_eval["picks"] if "Round 1" in p["name"]), None)
                pick_string = f" + their {r1_pick['name']}" if r1_pick else " + Draft Picks"
                
                recommendations.append({
                    "target_team": target_team_name, # Updated variable
                    "type": "🚀 Keeper Consolidation",
                    "deal": f"Send {my_eval['surplus_keeper']['name']} ({my_eval['surplus_keeper']['market_value']}) for a Top Rental{pick_string}",
                    "logic": f"You can't keep {my_eval['surplus_keeper']['name']}. They need a 3rd keeper and have capital to spend."
                })

        specific_deals = generate_trade_packages(my_eval, their_eval)
        for deal in specific_deals:
            tax_str = f"accounts for a {int(deal['tax']*100)}% roster spot tax and " if deal['tax'] > 0 else "is a direct value match and "
            recommendations.append({
                "target_team": target_team_name, # Updated variable
                "type": f"🤝 {deal['label']}",
                "deal": f"Offer {deal['offer']} \n**For:** {deal['receive']}",
                "logic": f"Total effective value {tax_str}meets the 65% minimum anchor rule."
            })

    return recommendations