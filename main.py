from flask import Flask
import os
import datetime
import yfinance as yf
import pandas as pd
from telegram import Bot
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

def run_bot():
    STOCK_SYMBOL = "AAPL"
    today = datetime.date.today()
    start = today - datetime.timedelta(days=100)

    df = yf.download(STOCK_SYMBOL, start=start)
    if df.empty or len(df) < 20:
        return { "error": "Not enough data." }

    df["sma5"] = df["Close"].rolling(window=5).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    latest = df.iloc[-1]
    if pd.notna(latest["rsi"]) and pd.notna(latest["sma5"]):
        if latest["rsi"] < 30 and latest["Close"] > latest["sma5"]:
            message = f"📈 BUY SIGNAL for {STOCK_SYMBOL}\nRSI: {latest['rsi']:.2f}, Close: ${latest['Close']:.2f}"
            bot.send_message(chat_id=CHAT_ID, text=message)

            order = MarketOrderRequest(
                symbol=STOCK_SYMBOL,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)
            return { "status": "Buy signal triggered and order placed." }

    return { "status": "No signal today." }

@app.route("/run-bot")
def trigger_bot():
    result = run_bot()
    return result

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
