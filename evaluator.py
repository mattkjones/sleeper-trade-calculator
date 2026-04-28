import pandas as pd
import itertools
import scraper
from utils import clean_name

def apply_keeper_premium(live_values, top_n=24, premium=1.15):
    sorted_items = sorted(live_values.items(), key=lambda x: x[1], reverse=True)
    adjusted_values = {}
    for i, (player, val) in enumerate(sorted_items):
        if i < top_n:
            adjusted_values[player] = val * premium
        else:
            adjusted_values[player] = val
    return adjusted_values

def get_team_valuation(roster):
    player_details = roster["player_details"]
    draft_picks = roster.get("draft_picks", [])
    raw_values = scraper.get_player_value_dict()
    
    live_values = apply_keeper_premium(raw_values, top_n=24, premium=1.15)
    
    for p in player_details:
        p_name_clean = clean_name(p["name"])
        p["market_value"] = int(live_values.get(p_name_clean, 500))
        
    sorted_p = sorted(player_details, key=lambda x: x["market_value"], reverse=True)
    
    # 🚨 UPDATED: Trimmed to 8 rounds
    base_pick_values = {
        1: 1450, 2: 950, 3: 650, 4: 450, 
        5: 300, 6: 200, 7: 125, 8: 75
    }
    evaluated_picks = []
    
    for p in draft_picks:
        rnd = p['round']
        slot = p.get('pick_slot')
        season = p.get('season', '2026')
        
        if slot and season == "2026":
            multiplier = {1: 100, 2: 50, 3: 35, 4: 20, 5: 10}.get(rnd, 0)
            slot_adjust = (4.5 - slot) * multiplier 
            val = base_pick_values.get(rnd, 0) + slot_adjust
            name = f"{season} Round {rnd} (Pick {slot})"
        else:
            years_out = int(season) - 2026
            base_val = base_pick_values.get(rnd, 0)
            val = base_val * (0.90 ** years_out)
            name = f"{season} Round {rnd} Pick"
            
        evaluated_picks.append({
            "name": name,
            "market_value": int(val),
            "is_pick": True,
            "season": int(season),
            "round": rnd
        })

    return {
        "keepers": sorted_p[:3],
        "keeper_score": sum(p["market_value"] for p in sorted_p[:3]),
        "surplus_keeper": sorted_p[3] if len(sorted_p) > 3 else None,
        "rentals": sorted_p[3:],
        "picks": sorted(evaluated_picks, key=lambda x: (x["season"], x["round"]))
    }

def generate_trade_packages(my_eval, their_eval):
    packages = []
    
    # 🚨 SAFETY FILTER: Only AI-evaluate picks worth > 200 (Roughly Round 5 and higher)
    usable_my_picks = [p for p in my_eval.get("picks", []) if p["market_value"] > 200]
    usable_their_picks = [p for p in their_eval.get("picks", []) if p["market_value"] > 200]
    
    my_pool = my_eval["rentals"][:4] + usable_my_picks
    their_pool = their_eval["keepers"] + their_eval["rentals"][:2] + usable_their_picks

    for my_len in [1, 2, 3]:
        for their_len in [1, 2]:
            for my_combo in itertools.combinations(my_pool, my_len):
                for their_combo in itertools.combinations(their_pool, their_len):
                    
                    my_names = set(i['name'] for i in my_combo)
                    their_names = set(i['name'] for i in their_combo)
                    if my_names.intersection(their_names):
                        continue
                        
                    my_players = [i for i in my_combo if not i.get("is_pick", False)]
                    their_players = [i for i in their_combo if not i.get("is_pick", False)]
                    
                    if len(my_players) == 0 and len(their_players) == 0:
                        continue
                        
                    net_roster_spots = len(my_players) - len(their_players)
                    if net_roster_spots < 0:
                        continue
                        
                    my_raw_val = sum(i["market_value"] for i in my_combo)
                    their_raw_val = sum(i["market_value"] for i in their_combo)
                    
                    my_best_item = max((i["market_value"] for i in my_combo), default=0)
                    their_best_item = max((i["market_value"] for i in their_combo), default=0)
                    
                    if their_raw_val * 0.90 <= my_raw_val <= their_raw_val * 1.15:
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
                                "value_diff": abs(my_raw_val - their_raw_val),
                                "label": t_type
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

def find_vibe_trades(my_roster, other_rosters, my_user_id, league_users):
    my_eval = get_team_valuation(my_roster)
    recommendations = []

    for team in other_rosters:
        if team["owner_id"] == my_user_id: 
            continue
        
        their_eval = get_team_valuation(team)
        
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
                    "target_team": target_team_name,
                    "type": "🚀 Keeper Consolidation",
                    "deal": f"Send {my_eval['surplus_keeper']['name']} ({my_eval['surplus_keeper']['market_value']}) for a Top Rental{pick_string}",
                    "logic": f"You can't keep {my_eval['surplus_keeper']['name']}. They need a 3rd keeper and have capital to spend."
                })

        specific_deals = generate_trade_packages(my_eval, their_eval)
        for deal in specific_deals:
            recommendations.append({
                "target_team": target_team_name,
                "type": f"🤝 {deal['label']}",
                "deal": f"Offer {deal['offer']} \n**For:** {deal['receive']}",
                "logic": f"Total value is a direct match and meets the 65% minimum anchor rule."
            })

    return recommendations

def evaluate_custom_trade(side_a_assets, side_b_assets, team_a_name, team_b_name):
    eff_a = sum(a['market_value'] for a in side_a_assets)
    eff_b = sum(b['market_value'] for b in side_b_assets)

    players_a = sum(1 for a in side_a_assets if not a.get('is_pick', False))
    players_b = sum(1 for b in side_b_assets if not b.get('is_pick', False))

    best_a = max([a['market_value'] for a in side_a_assets] + [0])
    best_b = max([b['market_value'] for b in side_b_assets] + [0])

    if eff_a == 0 and eff_b == 0:
         return {"status": "Empty", "blurb": "Select assets to evaluate.", "color": "normal"}

    val_diff = abs(eff_a - eff_b)
    
    winner = team_b_name if eff_a > eff_b else team_a_name
    loser = team_a_name if eff_a > eff_b else team_b_name

    color = "normal"
    if val_diff <= 100:
        status = "⚖️ Fair Trade"
        color = "success"
    elif val_diff <= 200:
        status = f"⚠️ This trade slightly favors {winner}."
        color = "warning"
    elif val_diff <= 350:
        status = f"🚨 This trade significantly favors {winner}."
        color = "error"
    else:
        status = f"💀 {loser} is getting fleeced, this trade needs adjusting!"
        color = "error"

    anchor_met = True
    anchor_msg = ""
    if players_a > players_b and players_b > 0:
        if best_a < best_b * 0.65:
            anchor_met, anchor_msg = False, f"{team_a_name}'s best player is too weak to anchor this package."
    elif players_b > players_a and players_a > 0:
        if best_b < best_a * 0.65:
            anchor_met, anchor_msg = False, f"{team_b_name}'s best player is too weak to anchor this package."

    if not anchor_met:
        status = "❌ Unfair (Rejected by Anchor Rule)"
        color = "error"

    blurb = f"**Value Sent:** {team_a_name} ({int(eff_a)}) vs {team_b_name} ({int(eff_b)})."

    if not anchor_met: blurb += f"\n\n**Rule Failed:** {anchor_msg}"

    return {"status": status, "blurb": blurb, "color": color}