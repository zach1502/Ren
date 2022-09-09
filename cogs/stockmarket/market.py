from math import floor, ceil
import asyncio
import time
import datetime
import matplotlib.pyplot as plt
import yfinance as yf  # pip install yfinance
import discord
from datetime import datetime

from redbot.core import bank, commands, Config
from redbot.core.utils.chat_formatting import box

from cogs.stockmarket.constants import (
    MAX_MSG_LENGTH,
    BROKER_NAME,
    PRICE_MULTIPLIER,
    EMBED_LOCATION,
    INVALID_INTERVAL_STR,
    INVALID_PERIOD_STR,
    INVALID_AMOUNT_STR,
    INVALID_TICKER_STR,
    POOR_STR,
    NO_TICKER_DATA_STR,
)
from cogs.stockmarket.utils import market_utils, InvalidInterval, InvalidPeriod, NoTickerData


# 80 Char line
###############################################################################
# To Do:
# 1. REFRACTOR
# 2. Make not spaghetti
# 3. Make pythonic


class Market(commands.Cog, market_utils):
    """The Market class contains all the commands that well,
    connect the bot to the stock markets all around the world.

    Supported markets:
    - All markets
    - All commodity futures
    - All indices
    - All ETFs
    - 9000+ cryptocurrencies

    Not supported:
    - Mutual Funds
    - After Hours and Premarket Trading

    [p] -> insert your prefix here
    The commands are:
    [p]market accountcreate - Creates a new account for the user
    [p]market holdings - Displays the user's holdings
    [p]market buy <ticker> - Buys a stock #Note: feels clunky, might as well add an <amount> param
    [p]market sell <ticker> - Sells a stock #Note: ^^^
    [p]market info <ticker> - Displays information about a stock WIP
    [p]market chart <ticker> - Displays a chart of a stock
    """

    start = 0
    end = 0

    member_data = {"transactions": [], "holdings": [], "total_contribution": 0}

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=835888251, force_registration=True)
        self.config.register_member(**self.member_data)
        self.enable_bg_loop()

    def enable_bg_loop(self):
        """Enables the background loop"""
        self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())

    def cog_unload(self):
        """Clean up when cog shuts down."""
        if self.bg_loop_task:
            self.bg_loop_task.cancel()

    async def bg_loop(self):
        """Background loop to check for dividends and pay it out when it comes time"""
        await self.bot.wait_until_ready()
        while True:
            await self.check_events()
            await asyncio.sleep(86400)

    @commands.group()
    async def market(self, ctx: commands.Context):
        """Manage your Money! Manage your Life! Invest into the FUTURE!
        This collection of commands allow you to invest your hard earned money,
        into any publicly traded company around the world! #GetRichSlow
        """
        pass

    @market.command(name="sell", aliases=["s"])
    async def sell_stock(
        self,
        ctx: commands.Context,
        ticker: str,
        amount_to_sell: int,
        member_object: discord.Member = None,
    ):
        """Sell a user-specified amount of a stock"""
        ticker = ticker.upper()

        if member_object is None:
            member_object = ctx.author

        async with self.config.member(ctx.author).holdings() as holdings:
            for holding in holdings:
                if holding["ticker"] == ticker:
                    amount_owned = holding["amount"]

                    ticker_info = await self.yf_ticker_info(ticker)
                    price = ticker_info["regularMarketPrice"]

                    if price is None:
                        await ctx.send(INVALID_TICKER_STR)
                        return

                    price = ceil(price * PRICE_MULTIPLIER)
                    currency_name = await bank.get_currency_name(ctx.guild)

                    if amount_to_sell > amount_owned:
                        await ctx.send(f"You do not have that many shares of {ticker}!")
                        return
                    elif amount_to_sell <= 0:
                        await ctx.send(INVALID_AMOUNT_STR)
                        return
                    else:
                        await self.sell(
                            ctx,
                            amount_to_sell,
                            holding,
                            holdings,
                            ticker,
                            price,
                            currency_name,
                        )
                        await self.log_sell(
                            ctx, ticker, amount_to_sell, price, amount_to_sell * price
                        )
                        return

    @market.command(name="buy", aliases=["b"])
    async def buy_stock(
        self,
        ctx: commands.Context,
        ticker: str,
        amount_to_buy: int,
        member_object: discord.Member = None,
    ):
        """
        Buy a stock! The specified ticker may require a suffix representing the exchange.
        By default, its assumed to be in the American stock exchanges. (NASDAQ, NYSE, AMEX)

        Toronto Stock Exchange (TSX) = .to
        TSX Venture Exchange (TSXV) = .v
        Shanghai Stock Exchange (SSE) = .ss
        Tokyo Stock Exchange (TYO) = .t
        Hong Kong Stock Exchange (HKSE) = .hk
        Shenzhen Stock Exchange (SZSE) = .sz
        Swiss Stock Exchange (SwSE) = .sw
        Paris Stock Exchange (PSE) = .par
        London Stock Exchange (LSE) = .l

        Tickers for companies may be searched for on https://ca.finance.yahoo.com/
        Tickers are case-insensitive
        """
        ticker = ticker.upper()

        if member_object is None:
            member_object = ctx.author

        ticker_info = await self.yf_ticker_info(ticker)

        price = ticker_info["regularMarketPrice"]

        if await self.is_invalid_ticker(ticker_info):
            await ctx.send(INVALID_TICKER_STR)
            return

        price = ceil(price * PRICE_MULTIPLIER)

        # Get current price
        balance = await bank.get_balance(ctx.author)
        maximum_purchasable = floor(balance / price)

        if maximum_purchasable == 0:
            await ctx.send(POOR_STR)
            return

        if amount_to_buy <= 0:
            await ctx.send(INVALID_AMOUNT_STR)
            return

        if amount_to_buy > 0:
            await self.buy(ctx, amount_to_buy, price, ticker, None)
            await self.log_buy(ctx, ticker, amount_to_buy, price, amount_to_buy * price)

    @market.command(name="holdings", aliases=["portfolio", "p"])
    async def list_holdings(self, ctx: commands.Context, member_object: discord.Member = None):
        """Lists all of your stocks and everything else that is in your portfolio"""

        async with self.config.member(ctx.author).holdings() as holdings:
            if not holdings:
                await ctx.send(f"{ctx.author.mention} you do not own any shares!")
                return

            # port_value = 0
            msg_title = "You own the following stocks:\n"
            msg = ""

            # print(holdings)

            for holding in holdings:
                ticker = holding["ticker"]
                amount = holding["amount"]
                msg += f"[{amount}] shares of [{ticker}]\n"

                # getting the ticker info takes way to long. thinking about creating a cache filled with ticker info
                # port_value += amount * ceil(yf.Ticker(ticker).info['regularMarketPrice'] * PRICE_MULTIPLIER)

        # port_value = str(port_value) + " " + await bank.get_currency_name(ctx.guild)
        # msg += f'\n your portfolio\'s total value is: {port_value}!```'

        await ctx.send(box(msg_title + msg, lang="css"))

    # chart
    @market.command(name="chart", aliases=["c"])
    async def get_chart(
        self, ctx: commands.Context, ticker: str, period_str: str = "1d", interval_str: str = "5m"
    ):
        """
        Gets a chart of a stock, period and interval can be specified
        Valid Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        Valid Intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """

        try:
            await self.get_embed_chart(ticker, period_str.lower(), interval_str.lower())
        except InvalidPeriod:
            await ctx.send(INVALID_PERIOD_STR)
            return
        except InvalidInterval:
            await ctx.send(INVALID_INTERVAL_STR)
            return
        except NoTickerData:
            await ctx.send(NO_TICKER_DATA_STR)
            return
        except Exception as e:
            await ctx.send(e)
            print(e)
            return

        await ctx.send(file=discord.File(EMBED_LOCATION, filename=ticker + ".jpg"))

    # Simple Information
    @market.command(name="info", aliases=["i"])
    async def get_info(self, ctx: commands.Context, ticker: str):
        """Gets information about a particular stock"""
        ticker = ticker.upper()
        info = await self.yf_ticker_info(ticker)
        # print(info)

        embed = await self.build_embed(
            ctx, ceil(info["regularMarketPrice"] * PRICE_MULTIPLIER), ticker, info
        )
        short_name = info["shortName"]
        embed.set_footer(text=f"{ticker} - {short_name}")
        try:
            summary = info["longBusinessSummary"]
            summary = (
                (summary[:MAX_MSG_LENGTH] + "...") if len(summary) > MAX_MSG_LENGTH else summary
            )
            embed.add_field(name=f"About {ticker}", value=summary, inline=False)
        except KeyError:
            embed.add_field(
                name=f"About {ticker}",
                value=f"No information found for ticker {ticker}",
                inline=False,
            )

        await ctx.send(embed=embed)

    # Simple Information
    @market.command(name="transactions", aliases=["trans", "t", "history"])
    async def get_sinfo(self, ctx: commands.Context, num_results: int = 10):
        """lists the last num_results transactions for a member"""

        async with self.config.member(ctx.author).transactions() as transactions:
            if not transactions:
                await ctx.send(f"{ctx.author.mention} you have not made any transactions!")
                return

            if num_results > len(transactions):
                num_results = len(transactions)

            msg = f"{ctx.author.mention} your last {num_results} transactions:\n"
            msg += "```css\n"
            for transaction in transactions[-num_results:]:
                type_transaction = transaction["type"]
                ticker = transaction["ticker"]
                date_str = transaction["date"]

                if type_transaction == "buy":
                    msg += f'Bought   [{ticker:<8}] [{transaction["shares_bought"]:<8} shares] for {transaction["bought_price"]:<8} each @ {date_str}\n'
                elif type_transaction == "sell":
                    msg += f'Sold     [{ticker:<8}] [{transaction["shares_sold"]:<8} shares] for {transaction["sold_price"]:<8} each @ {date_str}\n'
                else:
                    if transaction["dividend_amount"] != 0:
                        msg += f'Dividend [{ticker:<8}] [{transaction["dividend_amount"]:<8}] @ {date_str}\n'
                    if transaction["split_ratio"] != 0:
                        msg += f'Split   [{ticker:<8}] [{transaction["split_ratio"]:<8}] @ {date_str}\n'

            msg += "```"

            await ctx.send(msg)

    @commands.admin()
    @market.command(name="debug")
    async def market_debug(self, ctx: commands.Context):
        """Debugging command, prints out the data for all members"""
        # print out all the data
        all_member_data = await self.config.all_members(guild=None)
        print(all_member_data)
        await ctx.send("Dumped data to console")

    @commands.admin()
    @market.command(name="clearuser")
    async def market_clear_user(self, ctx: commands.Context, member: discord.Member):
        """Debugging command, clears all the data for a user"""
        await self.config.member(member).clear()
        await ctx.send(f"Cleared all data for {member}")

    @commands.admin()
    @market.command(name="clearall")
    async def market_clear_all(self, ctx: commands.Context):
        """Debugging command, clears all the data for all users"""
        # print out all the data
        await self.config.clear_all_members()
        await ctx.send("Cleared all data for all users")

    async def pay_dividend(
        self,
        guild_object: discord.Guild,
        list_of_member_objects: list,
        dividend_due_per_share: int,
        shares_owned: int,
        ticker: str,
    ):
        currency_name = await bank.get_currency_name(guild_object)
        dividend_due = ceil(dividend_due_per_share * shares_owned * PRICE_MULTIPLIER)

        await bank.deposit_credits(list_of_member_objects[0], dividend_due)
        try:
            await list_of_member_objects[0].send(
                f"you have received a dividend of {dividend_due} {currency_name} from {ticker}!"
            )
        except (discord.Forbidden, discord.NotFound):
            print(
                f"Failed to notify user about receiving a dividend {list_of_member_objects[0].name} in guild {guild_object.name}"
            )

    async def pay_split(
        self,
        guild_object: discord.Guild,
        list_of_member_objects: list,
        split_due_per_share: float,
        holding: dict,
        ticker: str,
    ):
        holding["amount"] += holding["amount"] * split_due_per_share
        try:
            await list_of_member_objects[0].send(
                f"you have received a {split_due_per_share} split from {ticker}!"
            )
        except (discord.Forbidden, discord.NotFound):
            print(
                f"Failed to notify user about receiving a split {list_of_member_objects[0].name} in guild {guild_object.name}"
            )

    async def sell(
        self,
        ctx: commands.Context,
        amount_to_sell: int,
        holding: dict,
        holdings: list,
        ticker: str,
        price: int,
        currency_name: str,
    ):
        holding["amount"] -= amount_to_sell
        if holding["amount"] == 0:
            holdings.remove(holding)

        current_contribution = await self.config.member(ctx.author).total_contribution()
        await self.config.member(ctx.author).total_contribution.set(
            current_contribution - amount_to_sell * price
        )

        embed = discord.Embed(
            color=0x00FF00,
            title=BROKER_NAME,
            description=f"""You have sold {amount_to_sell}
                                shares of {ticker} at {price} {currency_name} each,
                                for a total of {amount_to_sell * price} {currency_name}""",
        )

        old = await bank.get_balance(ctx.author)
        new = await bank.deposit_credits(ctx.author, amount_to_sell * price)

        embed.add_field(name="Previous Balance:", value=old)
        embed.add_field(name="New Balance:", value=new)
        await ctx.send(embed=embed)

    async def buy(
        self,
        ctx: commands.Context,
        amount_to_buy: int,
        price: int,
        ticker: str,
        sent_message: discord.Message = None,
    ):
        new_embed = discord.Embed(
            color=0x00FF00, title=BROKER_NAME, description="Shares Purchased!"
        )
        if sent_message != None:
            await sent_message.edit(embed=new_embed)
        else:
            await ctx.send(embed=new_embed)
        await bank.withdraw_credits(ctx.author, amount_to_buy * price)

        # add stock to portfolio
        previous_contribution = await self.config.member(ctx.author).total_contribution()
        await self.config.member(ctx.author).total_contribution.set(
            previous_contribution + amount_to_buy * price
        )

        async with self.config.member(ctx.author).holdings() as holdings:
            for holding in holdings:
                if holding["ticker"] == ticker:
                    holding["amount"] += amount_to_buy
                    return

            holdings.append(
                {"ticker": ticker, "amount": amount_to_buy, "initial DOP": time.time()}
            )

    async def check_events(self):
        """Checks if any events are due and pays them out"""

        # Surely there's something better than this
        all_member_data = await self.config.all_members(guild=None)
        for singular_guild_id in all_member_data:
            await self.for_each_member(singular_guild_id, all_member_data)

    async def for_each_member(self, singular_guild_id, all_member_data):
        for singular_member_id in all_member_data[singular_guild_id]:
            member_dict = all_member_data[singular_guild_id][singular_member_id]

            await self.for_each_holding(member_dict, singular_guild_id, singular_member_id)

    async def for_each_holding(self, member_dict, singular_guild_id, singular_member_id):
        for holding in member_dict["holdings"]:

            ticker = holding["ticker"]
            actions = await self.yf_ticker_actions(ticker)

            date = str(actions.index[-1])[:-9]
            most_recent_unix = time.mktime(
                datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()
            )

            current_unix = time.time()

            # claimable events
            if await self.is_event_claimable(
                current_unix, most_recent_unix, holding["initial DOP"]
            ):
                self.claim_event(
                    actions, holding, singular_guild_id, singular_member_id, member_dict, ticker
                )

    async def claim_event(
        self, actions, holding, singular_guild_id, singular_member_id, member_dict, ticker
    ):
        # pay out the dividend and/or split
        dividend_due_per_share = ceil(actions.iloc[-1][0] * PRICE_MULTIPLIER)
        split_due_per_share = actions.iloc[-1][1]

        shares_owned = holding["amount"]

        guild_object = self.bot.get_guild(singular_guild_id)
        list_of_member_objects = await guild_object.query_members(user_ids=singular_member_id)

        # list_of_member_objects should only contain one member
        if list_of_member_objects == None:
            return

        # pay dividend
        if dividend_due_per_share > 0:
            await self.pay_dividend(
                guild_object,
                list_of_member_objects,
                dividend_due_per_share,
                shares_owned,
                ticker,
            )

        # pay split
        if split_due_per_share > 0:
            await self.pay_split(
                guild_object,
                list_of_member_objects,
                split_due_per_share,
                holding,
                ticker,
            )

        # for history
        await self.log_event(
            member_dict,
            ticker,
            ceil(dividend_due_per_share * shares_owned),
            split_due_per_share,
        )
