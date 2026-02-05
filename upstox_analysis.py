
import os
import time
import requests
import gzip
import json
import io
import upstox_client
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# --- Configuration ---
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN") # Ensure you have this in .env or handle auth flow
# Note: In a real app, you would handle the OAuth flow to get the access token dynamically.

# --- Constants ---
NIFTY_50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFC", "INFY", "ITC", "LT", "HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN",
    "BHARTIARTL", "ASIANPAINT", "MARUTI", "TITAN", "BAJFINANCE", "HCLTECH", "ADANIENT", "SUNPHARMA",
    "ONGC", "NTPC", "TATAMOTORS", "POWERGRID", "ULTRACEMCO", "JSWSTEEL", "TATASTEEL", "M&M",
    "WIPRO", "COALINDIA", "BAJAJFINSV", "BPCL", "NESTLEIND", "BRITANNIA", "TECHM", "EICHERMOT",
    "ADANIPORTS", "GRASIM", "HINDALCO", "DRREDDY", "DIVISLAB", "CIPLA", "APOLLOHOSP", "TATACONSUM",
    "INDUSINDBK", "UPL", "HEROMOTOCO", "BAJAJ-AUTO", "HDFCLIFE", "SBILIFE", "AXISBANK", "LTIM"
]

def get_instrument_master(exchange):
    """Downloads and parses the Instrument Master JSON for NSE or BSE."""
    url = f"https://assets.upstox.com/market-quote/instruments/exchange/{exchange}.json.gz"
    print(f"Downloading {exchange} Instruments Master...")
    try:
        response = requests.get(url)
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            data = json.load(f)
        print(f"Success! Downloaded {len(data)} instruments from {exchange}.")
        return data
    except Exception as e:
        print(f"Error downloading {exchange} master: {e}")
        return []

def flatten_list(input_list):
    """Recursively flattens a nested list."""
    flat = []
    for item in input_list:
        if isinstance(item, list):
            flat.extend(flatten_list(item))
        else:
            flat.append(item)
    return flat

def get_target_instrument_keys():
    """Filters NSE and BSE data to find Nifty 50 stocks and Sensex indices."""
    
    # 1. Download Master Files
    nse_data = get_instrument_master("NSE")
    bse_data = get_instrument_master("BSE")
    
    # 2. Filter NSE Data (Nifty 50 Stocks)
    nifty_keys = []
    for item in nse_data:
        # We look for stocks (NSE_EQ) that are in our target list
        if item['segment'] == 'NSE_EQ' and item['trading_symbol'] in NIFTY_50_SYMBOLS:
            nifty_keys.append(item['instrument_key'])
            
    # 3. Filter BSE Data (All Indices)
    # Note: User wants ALL BSE Indices (Sensex, Bankex, etc.)
    bse_index_keys = []
    for item in bse_data:
        if item['segment'] == 'BSE_INDEX':
            bse_index_keys.append(item['instrument_key'])
            
    # 4. Combine and Clean
    # Use flatten_list just in case, though logically they should be flat now
    combined_dirty = nifty_keys + bse_index_keys
    flat_keys = flatten_list(combined_dirty)
    unique_keys = list(set(flat_keys))
    
    print(f"Total Unique Instruments identified: {len(unique_keys)}")
    return unique_keys

def fetch_historical_data(instrument_keys):
    """Fetches monthly candle data for the list of instruments."""
    
    # Setup Upstox Client
    configuration = upstox_client.Configuration()
    configuration.access_token = ACCESS_TOKEN
    api_instance = upstox_client.HistoryV3Api(upstox_client.ApiClient(configuration))
    
    candle_data = []
    
    print(f"Fetching historical data for {len(instrument_keys)} instruments...")
    
    # Note: Hardcoded dates as per user request (Jan 2025 - Feb 2026)
    # In production, use datetime.now() logic
    FROM_DATE = "2025-01-01"
    TO_DATE = "2026-02-05" 
    
    for i, key in enumerate(instrument_keys):
        try:
            response = api_instance.get_historical_candle_data1(
                key,
                "months", 
                "1", 
                TO_DATE, 
                FROM_DATE
            )
            
            if response.status == 'success' and response.data and response.data.candles:
                candle_data.append({
                    "instrument_key": key,
                    "payload": response.to_dict() # Serialize for storage/printing
                })
            else:
                print(f"Warning: No data for {key}")
                
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            
        # Rate Limiting: Sleep to avoid hitting API limits
        time.sleep(0.2) 
        
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}...")

    print("Data fetch complete.")
    return candle_data

def main():
    if not ACCESS_TOKEN:
        print("Error: UPSTOX_ACCESS_TOKEN not found in .env. Please authenticate first.")
        # In a real app, trigger the login flow here
        return

    # 1. Get List of Keys
    keys = get_target_instrument_keys()
    
    # 2. Fetch Data
    if keys:
        history_data = fetch_historical_data(keys)
        
        # 3. Summary
        print(f"\n--- Summary ---")
        print(f"Fetched valid data for {len(history_data)} instruments.")
        if history_data:
            print("Sample Entry Key:", history_data[0]['instrument_key'])
            # Here you would typically save this to a file or pass to the LLM
            
if __name__ == "__main__":
    main()
