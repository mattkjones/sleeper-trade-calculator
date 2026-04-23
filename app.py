import streamlit as st
import sleeper_logic as sl
import evaluator as ev

st.set_page_config(page_title="Sleeper Trade Engine", layout="wide")

with st.sidebar:
    st.header("Settings")
    username = st.text_input("Sleeper Username", value="mattkjones")

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
                
                if my_user_info:
                    team_name = my_user_info.get("metadata", {}).get("team_name")
                    display_name = team_name if team_name else my_user_info.get("display_name")
                else:
                    display_name = username

                st.title(f"🏀 '{display_name}' Trade Engine")
                
                if my_roster:
                    my_eval = ev.get_team_valuation(my_roster)
                    
                    st.metric("Top 3 Keeper Market Score", f"{int(my_eval['keeper_score'])}")
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.write(f"### Your Assets")
                        st.caption("Sorted by Scraped Market Value")
                        
                        for p in my_eval["keepers"]:
                            st.success(f"👑 **{p['name']}** ({p['market_value']})")
                        
                        if my_eval["surplus_keeper"]:
                            st.warning(f"⚠️ **Surplus:** {my_eval['surplus_keeper']['name']} ({my_eval['surplus_keeper']['market_value']})")
                        
                        rentals = my_eval["rentals"][1:] if my_eval["surplus_keeper"] else my_eval["rentals"]
                        for p in rentals:
                            st.text(f"• {p['name']} ({p['market_value']})")
                            
                        if my_eval["picks"]:
                            st.write("---")
                            st.write("### 🎟️ Draft Capital")
                            for pick in my_eval["picks"]:
                                st.text(f"• {pick['name']} (Value: {pick['market_value']})")
                    
                    with col2:
                        st.write("### 📢 Suggested Moves")
                        
                        with st.spinner("Calculating Realistic Trades..."):
                            # 🚨 PASSED league_users INTO THE FUNCTION HERE
                            trades = ev.find_vibe_trades(my_roster, rosters, user_id, league_users)
                        
                        if trades:
                            for t in trades:
                                with st.container(border=True):
                                    st.write(f"**{t['type']}** with **{t['target_team']}**")
                                    st.info(t['deal'])
                                    st.caption(f"Reasoning: {t['logic']}")
                        else:
                            st.write("No 'fair' keeper trades found that meet the 65% Anchor Rule.")
            else:
                st.title("🏀 Fantasy Trade Engine")
                st.warning(f"Could not find a league named '{target_league_name}'.")
        else:
            st.title("🏀 Fantasy Trade Engine")
            st.warning("No active leagues found for this user.")