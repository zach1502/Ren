"""Separate file for constants. Cause this takes up too much space."""
import os

MAX_MSG_LENGTH = 1021
PRICE_MULTIPLIER = 100
BROKER_NAME = "Ren's Brokerage"
EMBED_LOCATION = os.path.join('cogs', 'stockmarket', 'chart.jpg')
VALID_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
VALID_INTERVALS = [
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "5d",
    "1wk",
    "1mo",
    "3mo",
]
INVALID_INTERVAL_STR = "Invalid interval. Valid intervals are: " + ", ".join(VALID_INTERVALS)
INVALID_PERIOD_STR = "Invalid period. Valid periods are: " + ", ".join(VALID_PERIODS)
TRANSACTION_CANCELLED_STR = "Transaction cancelled!"
INVALID_TICKER_STR = "Invalid ticker symbol!"
INVALID_AMOUNT_STR = "Invalid amount!"
NO_TICKER_DATA_STR = "No data for this ticker, period and interval!\nIf you are trying to get a chart over a large period and a small interval, try using a smaller period or larger interval."
POOR_STR = "You do not have enough money to buy this stock!"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
QUIPS = [
    "Ready to Donate your money to Wall Street I see?",
    "AAAAAAAAAAND IT'S GONE!",
    "Diamond Hands. :raised_hands: :gem:",
    "Look, I swear I have a Securities License.",
    "I'm maybe not a real broker, but I can help you with that!",
    "Wow, did you learn that from r/wallstreetbets?",
    "Stocks are the only thing I would willingly buy high and sell low",
    "Pssst, I have insider information on this stock!",
    "Nothing brings me more joy than receiving dividends!",
    "I found out that I can manipulate stock market. Whatever I bought, it went red.",
    "The best way to earn a million dollars is to invest 10 million",
    "Let's talk about my retirement plan",
    "100% Not a pyramid scheme!",
    "Technical analysis is the Astrology of the stock market",
    'Look! the "Evergreen Forest" Formation is forming in the charts!',
    "BUY BUY BUY!",
    "SELL SELL SELL!",
    "Buying and holding for the long run is the best strategy!",
    "Oh! Tell me more about your NFT collection!",
    "Something about THIS stocks feels good!",
    "Started from the bottom now we're here!",
    "Learn to Invest!",
    "Short my stock, I shorten your life. :knife: :knife: :knife:",
    "Value or Growth stocks? :thinking:",
    "I still don't how the market works, and at this point I'm afraid to ask.",
    "I am a financial genious!",
    "Since I own this stock, you should buy it!",
    "The more you invest, the more I will earn!",
    "By the time you're old enough to retire, you'll have more money than you think!",
    "You're poorer than you think. ScotiaBank.",
    "APES TOGETHER STRONG",
    "Welcome back summoner!",
    "You can't find great value even if you were in a Walmart.",
    "Donate money to your rich local broker today",
    "Do you know why the European stock markets are sliding down?, Greece.",
    "How to be rich. Step 1: Take out student loans, Step 2: Invest in stocks, Step 3: Profit!",
    "Anything I say here is not financial advice, I'm ren, not your adviser.",
    "$GME go BRRRRRRRRRRRRRRRRRRRRRR",
]
