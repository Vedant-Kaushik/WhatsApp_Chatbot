
from attrs import field
import os
import time
import requests
import gzip
import json
import io
from contextlib import asynccontextmanager
import upstox_client
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form
from datetime import datetime

# Load Environment Variables
load_dotenv()

# Database imports
from database.db import init_db, get_db
from database.market_repo import (
    insert_instruments,
    get_all_instruments,
    insert_historical_candles,
    get_historical_candles,
    log_trade_signal
)

# Lifespan event handler for database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    preload_historical_data()
    yield
    # Shutdown logic (if needed)
    pass

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))


# --- Configuration ---
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

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
    # Note: ALL BSE Indices (Sensex, Bankex, etc.)
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
    TO_DATE = datetime.now().strftime("%Y-%m-%d")
    
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


# --- Technical Analysis ---

def calculate_returns_and_sma(ltp, closes):
    # Use the price from 12 months ago if available, otherwise oldest
    lookback = min(12, len(closes))
    start_price = closes[-lookback]
    
    ret_1y = ((ltp - start_price) / start_price) * 100
    avg_3m = sum(closes[-3:]) / min(3, len(closes))
    trend = "BULLISH" if ltp > avg_3m else "BEARISH"
    sma_line = []
    for i in range(len(closes)):
        if i < 2:
            sma_line.append(None)
        else:
            sma_line.append(sum(closes[i-2:i+1]) / 3)
    return ret_1y, avg_3m, trend, sma_line


def calculate_support_resistance(highs, lows):
    recent_lows = lows[-6:]
    recent_highs = highs[-6:]
    support = min(recent_lows)
    resistance = max(recent_highs)
    return support, resistance


def calculate_atr(highs, lows, closes):
    true_ranges = []
    for i in range(len(closes)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        true_ranges.append(tr)
    atr = sum(true_ranges) / len(true_ranges)
    return atr


def analyze_volume_trend(closes, volumes):
    if len(closes) < 2:
        return "INSUFFICIENT_DATA"
    price_up = closes[-1] > closes[-2]
    volume_up = volumes[-1] > volumes[-2]
    
    if price_up and volume_up:
        return "STRONG_UPTREND (Price & Volume up)"
    elif price_up and not volume_up:
        return "WEAK_UPTREND (Price up but Volume down)"
    elif not price_up and volume_up:
        return "STRONG_DOWNTREND (Price & Volume down)"
    else:
        return "WEAK_DOWNTREND (Price & Volume both down)"


def calculate_technical_indicators(ltp, candles_chrono):
    if ltp is None or len(candles_chrono) < 2:
        return None
        
    closes = [c[4] for c in candles_chrono]
    lows = [c[3] for c in candles_chrono]
    highs = [c[2] for c in candles_chrono]
    volumes = [c[5] for c in candles_chrono]
    
    ret_1y, avg_3m, trend, sma_line = calculate_returns_and_sma(ltp, closes)
    support, resistance = calculate_support_resistance(highs, lows)
    atr = calculate_atr(highs, lows, closes)
    vol_trend = analyze_volume_trend(closes, volumes)
    
    return {
        "ret_1y": ret_1y,
        "avg_3m": avg_3m,
        "trend": trend,
        "support": support,
        "resistance": resistance,
        "atr": atr,
        "vol_trend": vol_trend,
        "sma_line": sma_line
    }

import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_professional_chart(stock_name, candles_chrono, metrics):
    dates = [c[0].split('T')[0] for c in candles_chrono]
    opens = [c[1] for c in candles_chrono]
    highs = [c[2] for c in candles_chrono]
    lows = [c[3] for c in candles_chrono]
    closes = [c[4] for c in candles_chrono]
    volumes = [c[5] for c in candles_chrono]
    
    # Create subplots: 2 rows, shared x-axis
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f"{stock_name} Price Metrics", "Volume"),
                        row_width=[0.2, 0.7])
    
    # 1. Candlestick
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        name="OHLC"
    ), row=1, col=1)
    
    # 2. SMA Line
    if any(metrics["sma_line"]):
        fig.add_trace(go.Scatter(
            x=dates, y=metrics["sma_line"], 
            mode='lines', name='3-Month SMA',
            line=dict(color='orange', width=2)
        ), row=1, col=1)
    
    # 3. Support & Resistance Lines
    fig.add_hline(y=metrics["support"], line_dash="dash", line_color="green", 
                  annotation_text="Support", row=1, col=1)
    fig.add_hline(y=metrics["resistance"], line_dash="dash", line_color="red", 
                  annotation_text="Resistance", row=1, col=1)
                  
    # 4. Volume Bar Chart
    colors = ['green' if close >= open_ else 'red' for close, open_ in zip(closes, opens)]
    fig.add_trace(go.Bar(
        x=dates, y=volumes, name="Volume", marker_color=colors
    ), row=2, col=1)
    
    fig.update_layout(
        title=f"Professional Technical Analysis: {stock_name} (1Y Return: {metrics['ret_1y']:.2f}%)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark", # Professional trading feel
        height=600,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("frontend_upstox.html", {"request": request})

def preload_historical_data():
    if not ACCESS_TOKEN:
        print("Error: UPSTOX_ACCESS_TOKEN not found! Cannot fetch data.")
        return
    
    # Initialize database on startup
    init_db()
    print("Database initialized!")
    print("Pre-fetching instrument master and historical data...")
    
    # 1. Get or download instrument master
    instruments = get_all_instruments()
    
    if not instruments or len(instruments) < 10:
        print("Master cache empty or outdated. Download fresh NSE/BSE instrument data...")
        target_keys = get_target_instrument_keys()
        
        # We need to map target_keys back to their full objects to store in DB
        nse_data = get_instrument_master("NSE")
        bse_data = get_instrument_master("BSE")
        
        instrument_objects = []
        for item in nse_data + bse_data:
            if item['instrument_key'] in target_keys:
                instrument_objects.append({
                    'instrument_key': item['instrument_key'],
                    'trading_symbol': item['trading_symbol'],
                    'segment': item['segment'],
                    'exchange': 'NSE' if item in nse_data else 'BSE',
                    'name': item.get('name')
                })
        
        insert_instruments(instrument_objects)
        print(f"Inserted/updated {len(instrument_objects)} instruments")
    else:
        print(f"Using cached {len(instruments)} instruments from database")
    
    instruments = get_all_instruments()
    target_keys = [inst['instrument_key'] for inst in instruments]
    
    # 2. Fetch historical data only if not cached
    for key in target_keys:
        candles = get_historical_candles(key, "2025-01-01")
        if not candles:
            print(f"Fetching missing historical data for {key}...")
            single_history = fetch_historical_data([key]) 
            if single_history:
                result = single_history[0]
                candles_list = result['candles']
                inserted = insert_historical_candles(key, candles_list)
                print(f"Inserted {inserted} candles")
            else:
                print(f"Failed to fetch data for {key}")
    
    print("Historical data cache populated successfully!")

@app.get("/analyze")
async def analyze_redirect(request: Request):
    # When a user hits reload on the analyze tab, redirect them back to home page
    # This prevents re-analysis on page refresh, which can cause duplicate signals in DB
    return RedirectResponse(url="/", status_code=302)

@app.post("/analyze",response_class=HTMLResponse)
def analyze_data(request: Request, amount: int = Form(...), time: int = Form(...)):
    instruments = get_all_instruments()
    target_keys = [inst['instrument_key'] for inst in instruments]
    
    if not target_keys:
        return RedirectResponse(url="/upstox/", status_code=302)

    # Fetch ONLY the super-fast live price right now
    ltp_with_names = get_ltp(target_keys)
    
    stock_metrics = []
    
    # Create a mapping for quick lookup of names/symbols
    instrument_map = {inst['instrument_key']: inst for inst in instruments}
    
    for key in target_keys:
        instrument_key = key
        inst_info = instrument_map.get(key, {})
        
        # Get candles from DB. They are dicts, need to convert to list format expected by technical analysis
        db_candles = get_historical_candles(key)
        
        if not db_candles:
            continue
            
        # The database already returns data in ASC order (Oldest -> Newest)
        # We keep it that way for technical analysis
        candles_chrono = [
            [c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume']] 
            for c in db_candles
        ]
        
        ltp = ltp_with_names.get(instrument_key) # Current Price
        
        #  technical analysis
        metrics = calculate_technical_indicators(ltp, candles_chrono)
        
        if metrics is None: continue
        
        stock_metrics.append({
            "key": instrument_key,
            "symbol": inst_info.get('trading_symbol', key),
            "name": inst_info.get('name', key),
            "ltp": ltp,
            "candles": candles_chrono,
            **metrics
        })
    
    # Sort to find the best 1Y return
    stock_metrics.sort(key=lambda x: x['ret_1y'], reverse=True)
    top_20 = stock_metrics[:20]
    
    if not top_20:
        raise Exception("No market data could be fetched from Upstox. Please try again later.")

    if time < 12:
        # Short-term: Prioritize low volatility (lowest ATR)
        best_stock = min(top_20, key=lambda x: x['atr'])
        reason = "lowest volatility (safest) among top performers, making it ideal for a short-term horizon"
    else:
        # Long-term: Prioritize highest 1-year return
        best_stock = max(top_20, key=lambda x: x['ret_1y'])
        reason = "highest 1-year return, making it ideal for maximizing long-term growth"

    stock_name = best_stock['symbol']
    full_name = best_stock['name']

    prompt = f"""Hey! You're a simple and friendly stock helper.

    A person wants to put ₹{amount} in a stock for {time} months.
    Based on their goal, I have selected {full_name} ({stock_name}) because it has the {reason}.

    Technical Stats for this stock:
    - Current Price: ₹{best_stock['ltp']}
    - Last Year's Growth: +{best_stock['ret_1y']:.1f}%
    - Current Market Trend: {best_stock['trend']}
    - Safety/Stability (ATR): {best_stock['atr']:.1f}

    Write a simple 3-4 sentence message to the user explaining why this stock is a good fit for their specific time horizon ({time} months) and amount (₹{amount}). 
    Use the reason I gave you ({reason}) as your main point.
    Keep it very simple and friendly, like you're talking to a friend. Do not use emojis in the main text, only use the specific one I ask for below.

    You MUST start your response with exactly this line:
    "Starting with your ₹{amount} at {time} months wait ⏳"

    And you MUST end your response with exactly this line:
    "Here's the chart to see how price moved!"
    """
    
    # -- Generate Plotly HTML Snippet for the selected stock --
    candlestick_html = generate_professional_chart(stock_name, best_stock['candles'], best_stock)
    
    result = llm.invoke(prompt).content
    
    # Log the AI signal to the database
    log_trade_signal({
        'instrument_key': best_stock['key'],
        'signal_type': 'BUY', # Defaulting to BUY since we're recommending it
        'recommended_amount': amount,
        'ltp_at_signal': best_stock['ltp'],
        'stock_name': stock_name,
        'reasoning': result
    })
    
    return templates.TemplateResponse("frontend_upstox.html", {
        "request": request, 
        "result": result,
        "candlestick_chart": candlestick_html,
        "amount": amount,
        "time": time
    })

