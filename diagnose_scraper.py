import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://hashtagbasketball.com/fantasy-basketball-dynasty-rankings"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("--- DIAGNOSTIC START ---")
print("1. Pinging the server...")
response = requests.get(URL, headers=headers)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print("\n2. Searching for the data table...")
    soup = BeautifulSoup(response.text, 'lxml')
    tables = soup.find_all('table')
    print(f"Found {len(tables)} table(s) in the HTML.")

    if len(tables) > 0:
        print("\n3. Testing data extraction...")
        try:
            # Try to read the first table we find
            df = pd.read_html(str(tables[0]))[0]
            print(f"Success! DataFrame loaded with {len(df)} rows.")
            print("\nColumns detected:")
            print(df.columns.tolist())
            print("\nFirst 3 players:")
            # Just print the first column to see what the names look like
            print(df.iloc[:, 0].head(3).tolist()) 
        except Exception as e:
            print(f"Failed to read the table into Pandas: {e}")
    else:
        print("FAIL: No tables found. The site might be using JavaScript/React to render the data dynamically.")
        
        # Let's peek at the HTML to see what they gave us
        print("\nSnippet of what the scraper actually saw:")
        print(soup.text[:500].strip())
else:
    print("FAIL: The server rejected the request. We might need rotating headers or cloudscraper.")
print("--- DIAGNOSTIC END ---")