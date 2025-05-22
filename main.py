from flask import Flask
import os
import datetime
import yfinance as yf
import pandas as pd
from telegram import Bot
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from ta.momentum import RSIIndicator

app = Flask(__name__)
STOCK_SYMBOL = "AAPL"

# Load credentials from environment variables
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

# Initialize API clients
bot = Bot(token=TELEGRAM_TOKEN)
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

def send_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def run_bot():
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=100)
        df = yf.download(STOCK_SYMBOL, start=start)

        if df.empty or len(df) < 20:
            return {"error": "Not enough data to evaluate"}

        # Flatten Close prices to avoid shape errors
        close = df["Close"].values.flatten()
        close_series = pd.Series(close)

        # Technical indicators
        rsi = RSIIndicator(close=close_series).rsi()
        sma5 = close_series.rolling(window=5).mean()

        # Create DataFrame manually to keep everything aligned
        df_indicators = pd.DataFrame({
            "Close": close,
            "rsi": rsi,
            "sma5": sma5
        })

        latest = df_indicators.iloc[-1]

        rsi_value = latest["rsi"]
        sma_value = latest["sma5"]
        close_price = latest["Close"]

        if pd.isna(rsi_value) or pd.isna(sma_value):
            return {"error": "Indicators not ready yet"}

        if float(rsi_value) < 30 and float(close_price) > float(sma_value):
            message = (
                f"📈 BUY SIGNAL for {STOCK_SYMBOL}!\n"
                f"RSI: {rsi_value:.2f}, Close: {close_price:.2f}, SMA(5): {sma_value:.2f}"
            )
            send_telegram(message)

            order = MarketOrderRequest(
                symbol=STOCK_SYMBOL,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)

            return {"signal": "buy"}
        else:
            return {"signal": "none"}

    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def home():
    return "✅ Trading bot is live!"

@app.route("/run-bot")
def trigger_bot():
    result = run_bot()
    if "error" in result:
        return f"⚠️ Error: {result['error']}", 500
    elif result["signal"] == "buy":
        return "✅ Buy signal sent!"
    else:
        return "No signal today."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
