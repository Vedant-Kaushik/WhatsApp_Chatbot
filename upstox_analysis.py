
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
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form

# Load Environment Variables
load_dotenv()
app=FastAPI()
templates = Jinja2Templates(directory="templates")
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


# --- Technical Analysis ---

def calculate_returns_and_sma(ltp, closes):
    start_price = closes[0]
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


# Create a Global Cache Dictionary
STOCK_CACHE = {
    "target_keys": [],
    "history_data": []
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("frontend_upstox.html", {"request": request})

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

@app.get("/analyze")
async def analyze_redirect():
    return RedirectResponse(url="/")

@app.post("/analyze",response_class=HTMLResponse)
def analyze_data(request: Request, amount: int = Form(...), time: int = Form(...)):
    # Retrieve the heavy, static data from our RAM cache instantly (0 latency)
    target_keys = STOCK_CACHE["target_keys"]
    history_data = STOCK_CACHE["history_data"]
    
    if not target_keys:
        return RedirectResponse(url="/upstox/", status_code=302)

    # Fetch ONLY the super-fast live price right now, because it changes every second
    ltp_with_names = get_ltp(target_keys)
    
    prompt = f"""You are a professional, objective financial analyst writing a brief report for a beginner.
The client wants to invest ₹{amount} for {time} months. 
I am going to provide you with the technical numbers for a top-performing stock on the market right now.
DO NOT use complicated financial jargon (like SMA, Support, Resistance, ATR, or Moving Averages).
Instead, translate these numbers into a clear, professional summary. Explain the stock's recent performance, the potential risks involved (based on volatility), and the current momentum (based on volume).
Keep your tone authoritative but accessible. Do not use slang, emojis, or overly enthusiastic words like 'superstar' or 'rollercoaster'. Keep it to 3-4 concise sentences.

CRITICAL INSTRUCTION: You MUST explicitly include a transitional sentence like "I have plotted a detailed visual graph for you below" or "Please refer to the chart I generated below for a visual breakdown." Make it sound like a natural part of a professional report.

DATA:
"""

    stock_metrics = []
    
    for candle_data in history_data:
        instrument_key = candle_data['instrument_key']
        candles = candle_data['candles']
        ltp = ltp_with_names.get(instrument_key) # Current Price
        
        candles_chrono = list(reversed(candles))

        #  technical analysis
        metrics = calculate_technical_indicators(ltp, candles_chrono)
        
        if metrics is None: continue
        
        stock_metrics.append({
            "key": instrument_key,
            "ltp": ltp,
            "candles": candles_chrono,
            **metrics
        })
    
    # Sort to find the best 1Y return
    stock_metrics.sort(key=lambda x: x['ret_1y'], reverse=True)
    top_performers = stock_metrics[:5]
    
    for s in top_performers:
        prompt += f"Stock: {s['key']} | Price: {s['ltp']} | 1Y Return: {s['ret_1y']:.2f}% | Trend: {s['trend']} | Support: {s['support']} | Resistance: {s['resistance']} | Volatility (ATR): {s['atr']:.2f} | Volume Trend: {s['vol_trend']}\n"
    
    # -- Generate Plotly HTML Snippet for the #1 Top Performer --
    best_stock = top_performers[0]
    stock_name = best_stock['key'].split('|')[-1]
    
    candlestick_html = generate_professional_chart(stock_name, best_stock['candles'], best_stock)
    
    result = llm.invoke(prompt).content
    
    return templates.TemplateResponse("frontend_upstox.html", {
        "request": request, 
        "result": result,
        "candlestick_chart": candlestick_html,
        "amount": amount,
        "time": time
    })

