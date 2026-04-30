import streamlit as st
import sleeper_logic as sl
import evaluator as ev

st.set_page_config(page_title="Sleeper Trade Engine", layout="wide")

# INITIALIZE SESSION STATE FOR DYNAMIC ROWS
if 'my_slots' not in st.session_state: st.session_state.my_slots = 1
if 'their_slots' not in st.session_state: st.session_state.their_slots = 1

with st.sidebar:
    st.header("⚙️ Settings")
    username = st.text_input("Sleeper Username", value="mattkjones")
    
    st.write("---")
    st.header("🧭 Navigation")
    # 🚨 REPLACED TABS WITH SIDEBAR NAVIGATION
    app_mode = st.radio("Choose a Tool:", ["🤖 AI Trade Suggestions", "🧮 Manual Calculator"])

if username:
    user_id = sl.get_user_id(username)
    if not user_id:
        st.title("🏀 Fantasy Trade Engine")
        st.error(f"User '{username}' not found. Check spelling!")
    else:
        players = sl.fetch_all_players()
        all_leagues = sl.get_leagues(user_id)
        
        if all_leagues:
            target_league_name = "Hookers and Hoopers"
            target_league = next((l for l in all_leagues if l["name"] == target_league_name), None)
            
            if target_league:
                l_id = target_league["league_id"]
                rosters = sl.get_mapped_rosters(l_id, players)
                league_users = sl.get_league_users(l_id)
                
                my_roster = next((r for r in rosters if r["owner_id"] == user_id), None)
                my_user_info = next((u for u in league_users if u["user_id"] == user_id), None)
                
                my_display_name = username
                if my_user_info:
                    team_name = my_user_info.get("metadata", {}).get("team_name")
                    my_display_name = team_name if team_name else my_user_info.get("display_name")

                st.title(f"🏀 '{my_display_name}' Trade Engine")
                
                if my_roster:
                    my_eval = ev.get_team_valuation(my_roster)
                    
                    # --- TOOL 1: AI SUGGESTIONS ---
                    if app_mode == "🤖 AI Trade Suggestions":
                        st.metric("Top 3 Keeper Market Score", f"{int(my_eval['keeper_score'])}")
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.write(f"### Your Assets")
                            for p in my_eval["keepers"]: st.success(f"👑 **{p['name']}** ({p['market_value']})")
                            if my_eval["surplus_keeper"]: st.warning(f"⚠️ **Surplus:** {my_eval['surplus_keeper']['name']} ({my_eval['surplus_keeper']['market_value']})")
                            rentals = my_eval["rentals"][1:] if my_eval["surplus_keeper"] else my_eval["rentals"]
                            for p in rentals: st.text(f"• {p['name']} ({p['market_value']})")
                            if my_eval["picks"]:
                                st.write("---")
                                st.write("### 🎟️ Draft Capital")
                                for pick in my_eval["picks"]: st.text(f"• {pick['name']} ({pick['market_value']})")
                        
                        with col2:
                            st.write("### 📢 Suggested Moves")
                            with st.spinner("Calculating Realistic Trades..."):
                                trades = ev.find_vibe_trades(my_roster, rosters, user_id, league_users)
                            
                            if trades:
                                for t in trades:
                                    with st.container(border=True):
                                        st.write(f"**{t['type']}** with **{t['target_team']}**")
                                        st.info(t['deal'])
                                        st.caption(f"Reasoning: {t['logic']}")
                            else:
                                st.write("No 'fair' keeper trades found.")

                    # --- TOOL 2: MANUAL CALCULATOR ---
                    elif app_mode == "🧮 Manual Calculator":
                        st.write("### Custom Trade Evaluator")
                        
                        my_all_assets = my_eval["keepers"] + my_eval["rentals"] + my_eval["picks"]
                        my_options_dict = {f"{a['name']} ({a['market_value']})": {"name": a["name"], "market_value": a["market_value"], "is_pick": a.get("is_pick", False)} for a in my_all_assets}
                        my_options_list = ["-- Select Asset --"] + list(my_options_dict.keys())
                        
                        other_teams = {}
                        for r in rosters:
                            if r["owner_id"] == user_id: continue
                            u_info = next((u for u in league_users if str(u.get("user_id")) == str(r["owner_id"])), None)
                            if u_info:
                                t_name = u_info.get("metadata", {}).get("team_name")
                                d_name = t_name if t_name else u_info.get("display_name")
                            else:
                                d_name = f"Team {r['roster_id']}"
                            other_teams[d_name] = r

                        calc_col1, calc_col2 = st.columns(2)
                        
                        with calc_col1:
                            st.subheader(my_display_name)
                            my_trade_assets = []
                            for i in range(st.session_state.my_slots):
                                choice = st.selectbox(f"Send Asset {i+1}", my_options_list, key=f"my_slot_{i}")
                                if choice != "-- Select Asset --":
                                    my_trade_assets.append(my_options_dict[choice])
                            
                            if st.session_state.my_slots < 5:
                                if st.button("➕ Add Send Asset", key="add_my"):
                                    st.session_state.my_slots += 1
                                    st.rerun()

                        with calc_col2:
                            target_team_name = st.selectbox("Target Team", list(other_teams.keys()))
                            target_roster = other_teams[target_team_name]
                            target_eval = ev.get_team_valuation(target_roster)
                            
                            target_all_assets = target_eval["keepers"] + target_eval["rentals"] + target_eval["picks"]
                            target_options_dict = {f"{a['name']} ({a['market_value']})": {"name": a["name"], "market_value": a["market_value"], "is_pick": a.get("is_pick", False)} for a in target_all_assets}
                            target_options_list = ["-- Select Asset --"] + list(target_options_dict.keys())
                            
                            target_trade_assets = []
                            for i in range(st.session_state.their_slots):
                                choice = st.selectbox(f"Receive Asset {i+1}", target_options_list, key=f"their_slot_{target_team_name}_{i}")
                                if choice != "-- Select Asset --":
                                    target_trade_assets.append(target_options_dict[choice])
                            
                            if st.session_state.their_slots < 5:
                                if st.button("➕ Add Receive Asset", key="add_their"):
                                    st.session_state.their_slots += 1
                                    st.rerun()

                        st.write("---")
                        
                        b_col1, b_col2, b_col3 = st.columns([1, 1, 1])
                        with b_col2:
                            eval_pressed = st.button("⚖️ Calculate Trade", use_container_width=True)

                        if eval_pressed:
                            if not my_trade_assets and not target_trade_assets:
                                st.warning("Please select assets on both sides.")
                            else:
                                result = ev.evaluate_custom_trade(my_trade_assets, target_trade_assets, my_display_name, target_team_name)
                                
                                st.write("---")
                                if result["color"] == "error": st.error(result["status"])
                                elif result["color"] == "success": st.success(result["status"])
                                elif result["color"] == "warning": st.warning(result["status"])
                                else: st.info(result["status"])
                                
                                st.write(result["blurb"])
            else:
                st.warning(f"Could not find a league named '{target_league_name}'.")
        else:
            st.warning("No active leagues found for this user.")