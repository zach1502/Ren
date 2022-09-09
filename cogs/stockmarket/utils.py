from math import ceil
import random
import datetime
import matplotlib.pyplot as plt
import yfinance as yf  # pip install yfinance
import discord
from datetime import datetime

from redbot.core import bank, commands, Config
from cogs.stockmarket.constants import (
    BROKER_NAME,
    DATE_FORMAT,
    PRICE_MULTIPLIER,
    EMBED_LOCATION,
    VALID_INTERVALS,
    VALID_PERIODS,
    TRANSACTION_CANCELLED_STR,
    QUIPS,
)


class MarketExceptions(Exception):
    """Base class for exceptions for this cog."""

    pass


class InvalidInterval(MarketExceptions):
    """Exception raised for invalid interval."""

    pass


class InvalidPeriod(MarketExceptions):
    """Exception raised for invalid period."""

    pass


class NoTickerData(MarketExceptions):
    """Exception raised for invalid tickers."""

    pass


class market_utils:
    def __init__(self):
        self.config = Config.get_conf(self, identifier=835888251, force_registration=True)

    async def is_invalid_ticker(self, ticker_info: dict):
        if ticker_info["regularMarketPrice"] is None:
            return True
        if ticker_info["quoteType"] == "INDEX":
            return True
        if ticker_info["quoteType"] == "MUTUAL FUND":
            return True

        return False

    async def cancel_transaction(self, sent_message: discord.Message):
        new_embed = discord.Embed(
            color=0xFF0000, title=BROKER_NAME, description=TRANSACTION_CANCELLED_STR
        )
        await sent_message.edit(embed=new_embed)

    async def is_event_claimable(
        self, current_unix: float, most_recent_event_unix: float, initial_DOP: float
    ):
        return current_unix < most_recent_event_unix < initial_DOP

    async def yf_download(self, ticker: str, period_str: str, interval_str: str):
        return yf.download(ticker, period=period_str, interval=interval_str)

    async def yf_ticker_info(self, ticker: str):
        return yf.Ticker(ticker).info

    async def yf_ticker_actions(self, ticker: str):
        return yf.Ticker(ticker).actions

    async def get_embed_chart(self, ticker: str, period_str: str = "1d", interval_str: str = "5m"):
        """Gets the chart of the requested stock"""

        if period_str not in VALID_PERIODS:
            print(f"{period_str} is not in {VALID_PERIODS}")
            raise InvalidPeriod(period_str)

        if interval_str not in VALID_INTERVALS:
            print(f"{interval_str} is not in {VALID_INTERVALS}")
            raise InvalidInterval(interval_str)

        plt.clf()
        ticker = ticker.upper()
        # Get the data.. takes like 0.2s
        data = await self.yf_download(ticker, period_str, interval_str)

        if data.empty:
            raise NoTickerData

        if len(data["Close"]) == 0:
            return False

        # Plot the data using the close data
        data["Close"].plot(color="red" if (data["Close"][0] - data["Close"][-1] > 0) else "green")

        plt.title(ticker)
        plt.ylabel("Price")
        plt.grid()

        # convert to webp????
        plt.savefig(EMBED_LOCATION, bbox_inches="tight")  # note: saved as .jpg
        return True

    # so messy...
    async def build_embed(self, ctx: commands.Context, price: int, ticker: str, ticker_info: dict):
        """Builds the embed"""
        currency_name = await bank.get_currency_name(ctx.guild)
        quote_type = ticker_info["quoteType"]

        embed = discord.Embed(
            color=0x424549,
            title=BROKER_NAME,
            description='*"' + QUIPS[random.randint(0, len(QUIPS) - 1)] + '"*',
        )

        embed.add_field(name="Ticker", value=ticker_info["shortName"] + "\n" + ticker, inline=True)
        embed.add_field(name="Current Price", value=str(price) + " " + currency_name, inline=True)
        embed.add_field(name="Investment Type", value=quote_type, inline=True)

        # "Special" fields
        if quote_type == "EQUITY":
            embed.add_field(name="Sector", value=ticker_info["sector"], inline=True)
            embed.add_field(name="Industry", value=ticker_info["industry"], inline=True)

            try:
                embed.add_field(
                    name="Trailing P/E", value=f"{ticker_info['trailingPE']:.2f}", inline=True
                )
            except KeyError:
                embed.add_field(name="Trailing P/E", value="NaN", inline=True)

        elif quote_type == "ETF":
            embed.add_field(name="Exchange", value=ticker_info["exchange"], inline=True)

            top_holdings = ""
            for key in range(0, 3):
                top_holdings += f"""{ticker_info['holdings'][key]['symbol']}:
                {ticker_info['holdings'][key]['holdingPercent'] * PRICE_MULTIPLIER:.2f}%\n"""
            if top_holdings == "":
                top_holdings = "NaN"
            embed.add_field(name="Top 3 Holdings", value=top_holdings, inline=True)

            embed.add_field(name="Assets Under Management", value=ticker_info["totalAssets"])

        embed.add_field(name="Open", value=ticker_info["open"], inline=True)
        embed.add_field(name="High", value=ticker_info["dayHigh"], inline=True)
        embed.add_field(name="Low", value=ticker_info["regularMarketDayLow"], inline=True)

        embed.add_field(name="52-Week Low", value=ticker_info["fiftyTwoWeekLow"], inline=True)
        embed.add_field(name="52-week high", value=ticker_info["fiftyTwoWeekHigh"], inline=True)
        embed.add_field(name="Volume", value=ticker_info["volume"], inline=True)

        embed.set_footer(text="Enter 0 to cancel")

        return embed

    def log_event(
        self, member_dict: dict, ticker: str, dividend_due: int, split_due_per_share: float
    ):
        member_dict["transactions"].append(
            {
                "type": "event",
                ticker: ticker,
                "date": datetime.utcnow().strftime(DATE_FORMAT),
                "dividend_amount": ceil(dividend_due),
                "split_ratio": split_due_per_share,
            }
        )

    async def log_sell(
        self,
        ctx: commands.Context,
        ticker: str,
        amount_to_sell: float,
        price: int,
        amount_received: int,
    ):
        async with self.config.member(ctx.author).transactions() as transactions:
            transactions.append(
                {
                    "type": "sell",
                    "ticker": ticker,
                    "date": datetime.utcnow().strftime(DATE_FORMAT),
                    "shares_sold": amount_to_sell,
                    "sold_price": price,
                    "amount_received": amount_received,
                }
            )

    async def log_buy(
        self,
        ctx: commands.Context,
        ticker: str,
        amount_to_buy: float,
        price: int,
        amount_spent: int,
    ):
        async with self.config.member(ctx.author).transactions() as transactions:
            transactions.append(
                {
                    "type": "buy",
                    "ticker": ticker,
                    "date": datetime.utcnow().strftime(DATE_FORMAT),
                    "shares_bought": amount_to_buy,
                    "bought_price": price,
                    "amount_spent": amount_spent,
                }
            )
