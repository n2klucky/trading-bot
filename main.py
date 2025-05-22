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

app = Flask(__name__)
STOCK_SYMBOL = "AAPL"

# Load secrets from environment variables
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

# Setup API clients
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
            return {"error": "Not enough data"}

        # Calculate RSI and SMA
        df["rsi"] = ta.momentum.RSIIndicator(close=df["Close"]).rsi()
        df["sma5"] = df["Close"].rolling(window=5).mean()

        latest = df.iloc[-1]

        # Convert to float scalars
        rsi_value = float(latest["rsi"]) if pd.notnull(latest["rsi"]) else None
        sma_value = float(latest["sma5"]) if pd.notnull(latest["sma5"]) else None
        close_price = float(latest["Close"]) if pd.notnull(latest["Close"]) else None

        if rsi_value is None or sma_value is None or close_price is None:
            return {"error": "Missing values in indicators"}

        if rsi_value < 30 and close_price > sma_value:
            message = (
                f"📈 BUY SIGNAL for {STOCK_SYMBOL}\n"
                f"RSI: {rsi_value:.2f}, Close: ${close_price:.2f}, SMA(5): ${sma_value:.2f}"
            )
            send_telegram(message)

            # Submit mock trade to Alpaca
            order = MarketOrderRequest(
                symbol=STOCK_SYMBOL,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order)

            return {"signal": "buy"}
        else:
