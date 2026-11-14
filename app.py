from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd

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

def detect_order_blocks(df):
    obs = []
    for i in range(2, len(df) - 2):
        prev_close = df['Close'].iloc[i-1]
        prev_open = df['Open'].iloc[i-1]
        curr_close = df['Close'].iloc[i]
        curr_open = df['Open'].iloc[i]
        
        # Bullish Order Block (Bearish candle followed by strong bullish move)
        if prev_close < prev_open and curr_close > curr_open:
            body_prev = abs(prev_open - prev_close)
            body_curr = abs(curr_close - curr_open)
            if body_curr > body_prev * 1.8:
                obs.append({
                    "type": "BULLISH",
                    "time": str(df.index[i-1]),
                    "high": round(float(df['High'].iloc[i-1]), 5),
                    "low": round(float(df['Low'].iloc[i-1]), 5)
                })
                
        # Bearish Order Block (Bullish candle followed by strong bearish move)
        elif prev_close > prev_open and curr_close < curr_open:
            body_prev = abs(prev_close - prev_open)
            body_curr = abs(curr_open - curr_close)
            if body_curr > body_prev * 1.8:
                obs.append({
                    "type": "BEARISH",
                    "time": str(df.index[i-1]),
                    "high": round(float(df['High'].iloc[i-1]), 5),
                    "low": round(float(df['Low'].iloc[i-1]), 5)
                })
    return obs[-5:] # সর্বশেষ ৫টি অর্ডার ব্লক দেখাবে

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_forex_data():
    momentum_list = []
    selected_pair = "EURUSD=X"
    
    for name, ticker in PAIRS.items():
        try:
            df = yf.download(ticker, period="5d", interval="1h", progress=False)
            if not df.empty and len(df) > 24:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                current_price = float(df['Close'].iloc[-1])
                prev_24h_price = float(df['Close'].iloc[-24])
                change_pct = ((current_price - prev_24h_price) / prev_24h_price) * 100
                momentum_list.append({
                    "name": name,
                    "ticker": ticker,
                    "price": round(current_price, 5),
                    "change": round(change_pct, 2)
                })
        except Exception:
            continue

    # শতাংশ পরিবর্তন অনুযায়ী সাজানো (সবচেয়ে বেশি পজিটিভ উপরে)
    momentum_list.sort(key=lambda x: x['change'], reverse=True)
    return jsonify(momentum_list)

@app.route('/api/chart/<ticker>')
def get_chart_data(ticker):
    df = yf.download(ticker, period="5d", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
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
