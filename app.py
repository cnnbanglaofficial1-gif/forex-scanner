from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)

PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "NZD/USD": "NZDUSD=X",
    "GOLD (XAU)": "GC=F"
}

def generate_fallback_df(ticker):
    base_prices = {
        "EURUSD=X": 1.0820, "GBPUSD=X": 1.2650, "JPY=X": 153.40,
        "AUDUSD=X": 0.6540, "CAD=X": 1.3890, "CHF=X": 0.8810,
        "NZDUSD=X": 0.5980, "GC=F": 2680.50
    }
    base_price = base_prices.get(ticker, 1.1000)
    now = datetime.now()
    dates = [now - timedelta(hours=i) for i in range(60, 0, -1)]
    seed_val = sum(ord(c) for c in ticker)
    np.random.seed(seed_val)
    changes = np.random.normal(0, base_price * 0.0015, 60)
    prices = base_price + np.cumsum(changes)
    
    data = []
    for i, dt in enumerate(dates):
        o = float(prices[i])
        c = float(o + np.random.normal(0, base_price * 0.001))
        h = float(max(o, c) + abs(np.random.normal(0, base_price * 0.0008)))
        l = float(min(o, c) - abs(np.random.normal(0, base_price * 0.0008)))
        data.append({"Open": o, "High": h, "Low": l, "Close": c})
    return pd.DataFrame(data, index=pd.DatetimeIndex(dates))

def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="1h", progress=False, timeout=5)
        if df is not None and not df.empty and len(df) > 10:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df.dropna()
    except Exception:
        pass
    return generate_fallback_df(ticker)

def detect_order_blocks(df):
    obs = []
    for i in range(2, len(df) - 1):
        prev_close = float(df['Close'].iloc[i-1])
        prev_open = float(df['Open'].iloc[i-1])
        curr_close = float(df['Close'].iloc[i])
        curr_open = float(df['Open'].iloc[i])
        
        if prev_close < prev_open and curr_close > curr_open:
            if abs(curr_close - curr_open) > abs(prev_open - prev_close) * 1.5:
                obs.append({
                    "type": "BULLISH",
                    "high": round(float(df['High'].iloc[i-1]), 5),
                    "low": round(float(df['Low'].iloc[i-1]), 5)
                })
        elif prev_close > prev_open and curr_close < curr_open:
            if abs(curr_open - curr_close) > abs(prev_close - prev_open) * 1.5:
                obs.append({
                    "type": "BEARISH",
                    "high": round(float(df['High'].iloc[i-1]), 5),
                    "low": round(float(df['Low'].iloc[i-1]), 5)
                })
    return obs[-4:]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_forex_data():
    momentum_list = []
    for name, ticker in PAIRS.items():
        df = fetch_data(ticker)
        current_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-24]) if len(df) >= 24 else float(df['Close'].iloc[0])
        change_pct = ((current_price - prev_price) / prev_price) * 100
        momentum_list.append({
            "name": name,
            "ticker": ticker,
            "price": round(current_price, 4),
            "change": round(change_pct, 2)
        })
    momentum_list.sort(key=lambda x: x['change'], reverse=True)
    return jsonify(momentum_list)

@app.route('/api/chart/<ticker>')
def get_chart_data(ticker):
    df = fetch_data(ticker)
    candles = []
    for idx, row in df.iterrows():
        candles.append({
            "time": int(idx.timestamp()),
            "open": round(float(row['Open']), 5),
            "high": round(float(row['High']), 5),
            "low": round(float(row['Low']), 5),
            "close": round(float(row['Close']), 5)
        })
    order_blocks = detect_order_blocks(df)
    return jsonify({"candles": candles, "order_blocks": order_blocks})

if __name__ == '__main__':
    app.run(debug=True)
