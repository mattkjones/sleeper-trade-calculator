import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import io
import streamlit as st
from utils import clean_name

# UPDATED URL
URL = "https://hashtagbasketball.com/keeper"

def scrape_dynamic_values():
    print(f"Scraping live trade values from {URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        
        html_stream = io.StringIO(response.text)
        tables = pd.read_html(html_stream)
        
        target_df = None
        
        for df in tables:
            if any("PLAYER" in str(col).upper() for col in df.columns):
                target_df = df
                break
                
        if target_df is None:
            print("Table with 'PLAYER' column not found. The website UI may have changed.")
            return None

        # Flatten the headers so the CSV saves correctly (MultiIndex fix)
        if isinstance(target_df.columns, pd.MultiIndex):
            target_df.columns = target_df.columns.get_level_values(-1)

        player_col = next(col for col in target_df.columns if "PLAYER" in str(col).upper())
        target_df[player_col] = target_df[player_col].astype(str).str.split('\(').str[0].str.strip()
            
        target_df.to_csv("live_market_values.csv", index=False)
        print("Scrape successful. Saved to live_market_values.csv")
        return target_df

    except Exception as e:
        print(f"Scraper failed: {e}")
        return None

@st.cache_data(ttl=3600)
def get_player_value_dict():
    if not os.path.exists("live_market_values.csv"):
        scrape_dynamic_values()
        
    try:
        df = pd.read_csv("live_market_values.csv")
        
        player_col = next((col for col in df.columns if "PLAYER" in str(col).upper()), None)
        # Expanded search to catch Z-scores, Totals, or general Values
        value_col = next((col for col in df.columns if any(v in str(col).upper() for v in ["TOTAL", "VALUE", "SCORE", "Z"])), None)
        
        if player_col and value_col:
             raw_dict = dict(zip(df[player_col], pd.to_numeric(df[value_col], errors='coerce')))
             return {clean_name(k): v for k, v in raw_dict.items() if pd.notna(v)}
        else:
             print(f"Could not find PLAYER or VALUE columns. Columns found: {df.columns.tolist()}")
             return {clean_name("Victor Wembanyama"): 2500, clean_name("Shai Gilgeous-Alexander"): 2400}
             
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return {clean_name("Victor Wembanyama"): 2500, clean_name("Shai Gilgeous-Alexander"): 2400}