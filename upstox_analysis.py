
from attrs import field
import os
import time
import requests
import gzip
import json
import io
import upstox_client
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

# Load Environment Variables
load_dotenv()
app=FastAPI()
# --- Configuration ---
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN") # Ensure you have this in .env or handle auth flow
# Note: In a real app, you would handle the OAuth flow to get the access token dynamically.

# Configure APIs
configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN
api_client = upstox_client.ApiClient(configuration)

history_api = upstox_client.HistoryV3Api(api_client)

market_api = upstox_client.MarketQuoteV3Api(api_client)

llm=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)

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
    target_keys = list(set(flat_keys))
    
    print(f"Total Unique Instruments identified: {len(target_keys)}")
    return target_keys

def fetch_historical_data(target_keys):
    """Fetches monthly candle data for the list of instruments."""
    
    candle_data = []
    
    print(f"Fetching historical data for {len(target_keys)} instruments...")
    
    # Note: Hardcoded dates as per user request (Jan 2025 - Feb 2026)
    # In production, use datetime.now() logic
    FROM_DATE = "2025-01-01"
    TO_DATE = "2026-03-04" 
    
    for i, key in enumerate(target_keys):
        try:
            response = history_api.get_historical_candle_data1(
                key,
                "months", 
                "1", 
                TO_DATE, 
                FROM_DATE
            )
            
            if response.status == 'success' and response.data and response.data.candles:
                candle_data.append({
                    "instrument_key": key,
                    "candles": response.data.candles # Serialize for storage/printing
                })
            else:
                print(f"Warning: No data for {key}")
                
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            
        # Rate Limiting: Sleep to avoid hitting API limits
        time.sleep(0.2) 
        
        
    print("Data fetch complete.")
    return candle_data

def get_ltp(target_keys):

    ltp_with_names = {}

    print("Fetching Live LTP...")

    for instrument_key in target_keys:
        
        try:
            # For a single instrument
            response = market_api.get_ltp(instrument_key=instrument_key)
            actual_keys = list(response.data.keys())
            ltp_with_names[instrument_key] = response.data[actual_keys[0]].last_price

        except Exception as e:
            # Using generic Exception to catch all
            print(f"Exception when calling MarketQuoteApi->get_ltp: {e}")

    print(f"Fetched LTP for {len(ltp_with_names)} instruments.")
    return ltp_with_names


# Create a Global Cache Dictionary
STOCK_CACHE = {
    "target_keys": [],
    "history_data": []
}

@app.on_event("startup")
def preload_historical_data():
    if not ACCESS_TOKEN:
        print("Error: UPSTOX_ACCESS_TOKEN not found! Cannot fetch data.")
        return
        
    print("Pre-fetching 1-year historical data...")
    target_keys = get_target_instrument_keys()
    
    # Save to global cache so all users can read it instantly
    STOCK_CACHE["target_keys"] = target_keys
    STOCK_CACHE["history_data"] = fetch_historical_data(target_keys)
    print("Historical Cache populated successfully!")


# 3. Fix your Endpoint to use the cache
class input_type(BaseModel):
    amount: int
    time: int

@app.post("/analyze")
def analyze_data(user_input: input_type):
    # Retrieve the heavy, static data from our RAM cache instantly (0 latency)
    target_keys = STOCK_CACHE["target_keys"]
    history_data = STOCK_CACHE["history_data"]
    
    if not target_keys:
        return {"error": "Server is still loading stock data or authentication failed."}

    # Fetch ONLY the super-fast live price right now, because it changes every second
    ltp_with_names = get_ltp(target_keys)
    
    prompt = f"Analyze these stocks given amount and time to invest\n\n amount :{user_input.amount} and time is {user_input.time} months\n\n\n make sure you use few words in 2 lines\n\n"

    for candle_data in history_data:
        instrument_key = candle_data['instrument_key']
        candles = candle_data['candles']
        ltp = ltp_with_names.get(instrument_key) # Current Price
        
        # all the analysis part
        # Calculate returns and trend...
        closes = [c[4] for c in candles] 
        start_price = closes[-1]
        ret_1y = ((ltp - start_price) / start_price) * 100
        avg_3m = sum(closes[:3]) / 3
        trend = "BULLISH" if ltp > avg_3m else "BEARISH"
        
        prompt += f"Stock: {instrument_key} | Price: {ltp} | 1Y Return: {ret_1y:.2f}% | Trend: {trend}\n"
    
    return llm.invoke(prompt).content

