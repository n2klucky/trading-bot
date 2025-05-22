from flask import Flask
import os
import datetime
import yfinance as yf
import pandas as pd
from telegram import Bot
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import ta

# === Setup ===
app = Flask(__name__)
STOCK_SYMBOL = "AAPL"

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

# === Telegram Alert ===
def send_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

# === Bot Logic ===
def run_bot():
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=100)
        df = yf.download(STOCK_SYMBOL, start=start)

        if df.empty or len(df) < 20:
            return {"error": "Not enough data to evaluate."}

        # Calculate RSI and SMA
        df["rsi"] = ta.momentum.RSIIndicator(close=df["Close"]).rsi()
        df["sma5"] = df["Close"].rolling(window=5).mean()

        latest = df.iloc[-1]
        rsi_value = float(latest["rsi"])
        sma5_value = float(latest["sma5"])
        close_price = float(latest["Close"])

        if rsi_value < 30 and close_price > sma5_value:
            message = f"📈 BUY SIGNAL for {STOCK_SYMBOL}!\nRSI: {rsi_value:.2f}, Close: {close_price:.2f}, SMA(5): {sma5_value:.2f}"
            send_telegram(message)

            order = MarketOrderRequest(
                symbol=STOCK_SYMBOL,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)

            return {"signal": "buy", "rsi": rsi_value, "close": close_price, "sma5": sma5_value}
        else:
            return {"signal": "none"}

    except Exception as e:
        return {"error": str(e)}

# === Routes ===
@app.route("/")
def home():
    return "✅ Trading bot is live!"

@app.route("/run-bot")
def trigger_bot():
    result = run_bot()
    if "error" in result:
        return f"⚠️ Error: {result['error']}", 500
    elif result["signal"] == "buy":
        return "✅ Buy signal triggered and sent to Telegram."
    else:
        return "No signal today."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
