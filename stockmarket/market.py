""" Here is the Module Docstring"""
from math import floor, ceil
import random
import json
import os
import asyncio
import time
import matplotlib.pyplot as plt
import yfinance as yf # pip install yfinance
import discord

from redbot.core import bank, commands, Config, checks
from redbot.core.utils.predicates import MessagePredicate

from .constants import Constants as const

#80 Char line
###############################################################################
# To Do:
# 1. REFRACTOR AND OPTIMIZE
# 2. Pretty up outputs with embeds
# 3. Dividends and splits are not yet implemented
# 4. Buy & Sell functions probably can be simplified somehow
# 5. Time is saved oddly, think its only because of the api but need to figure out why
# 6. buy/sell with the full company name instead of tickers

class Market(commands.Cog):
    """The Market class contains all the commands that well,
    connect the bot to the stock markets all around the world.

    Supported markets:
    - All markets
    - All futures
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
    [p]market buy <ticker> - Buys a stock
    [p]market sell <ticker> - Sells a stock
    [p]market info <ticker> - Displays information about a stock WIP
    [p]market chart <ticker> - Displays a chart of a stock
    """
    start = 0
    end = 0

    global_config = {
        "exdividend_days": [],
        "portfolios": []
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=835888249, force_registration=True)
        self.config.register_global(**self.global_config)
        self.enable_bg_loop()

    def enable_bg_loop(self):
        """Enables the background loop"""
        self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())

    def cog_unload(self):
        """Clean up when cog shuts down."""
        if self.bg_loop_task:
            self.bg_loop_task.cancel()

    async def dividend_check(self, data, ticker, amount_bought, user_id):
        """Checks if the ticker pays a dividend, if so, add to dict"""
        print("Checking for dividend!")
        try:
            exdividend = data['exDividendDate']
            print(exdividend)
        except KeyError:
            print("KeyError = No Dividend")
            return

        if exdividend is None:
            print("no date = No Dividend")
            return

        date = time.time()

        if date < exdividend and not await self.get_upcomming_dividends(user_id, amount_bought, ticker):
            reminder = {
                "user_id": user_id,
                "ticker": ticker,
                "amount": amount_bought,
                "exDividendDate": (exdividend + 1814400) # ex-dividend date + 3 weeks
                # I have no better way of implementing this atm
            }

            async with self.config.exdividend_days() as exdividend_day:
                exdividend_day.append(reminder)

    async def get_upcomming_dividends(self, user_id, amount_bought, ticker):
        """Checks if the user has any dividends of this stock in the future"""
        async with self.config.exdividend_days() as current_reminders:
            for reminder in current_reminders:
                if reminder['user_id'] == user_id and reminder['ticker'] == ticker:
                    reminder['amount'] += amount_bought
                    return True

        return False

    async def bg_loop(self):
        """Background loop to check for dividends and pay it out when it comes time"""
        await self.bot.wait_until_ready()
        while True:
            await self.check_dividends()
            await asyncio.sleep(5) # once a day will suffice 86400

    async def check_dividends(self):
        """Checks if any dividends are due and pays them out"""
        to_update = []
        saved_ticker_info = []

        now = time.time()
        print(now)

        for dividends in await self.config.exdividend_days():
            ticker_info = yf.Ticker(dividends['ticker']).info
            print(dividends)
            
            if dividends['exDividendDate'] < now:
                print("Depositing dividends!")

                # Hangs here?
                await bank.deposit_credits(dividends['ctx_author'], ceil(dividends['amount'] * ticker_info['lastDividendValue'] * 100))

                print("Dividends PAID!")
                to_update.append(dividends)
                saved_ticker_info.append(ticker_info)

        for index, paid_dividends in enumerate(to_update):
            async with self.config.exdividend_days() as dividends:
                if saved_ticker_info[index]['exDividendDate'] > paid_dividends['exDividendDate']:
                    paid_dividends['exDividendDate'] = saved_ticker_info[index]['exDividendDate']
                else:
                    dividends.remove(paid_dividends)

    async def load_portfolio(self, data, user_id):
        """Helper function to load the requested portfolio from the json file"""

        for portfolio in data['portfolios']:
            if portfolio['userId'] == user_id:
                return portfolio

        return None

    async def get_embed_chart(self, ticker, period_str = '1d', interval_str = '5m'):
        """Gets the chart of the requested stock"""
        plt.clf()
        ticker = ticker.upper()
        # Get the data.. takes like 0.2s
        data = yf.download(ticker, period = period_str, interval = interval_str)
        # data is a pandas dataframe
        print(data)

        if len(data['Close']) == 0:
            return False

        # Plot the data using the close data
        data['Close'].plot(color='red' if (data['Close'][0] - data['Close'][-1] > 0) else 'green')

        plt.title(ticker)
        plt.ylabel('Price')
        plt.grid()

        #convert to webp????
        plt.savefig(const.EMBED_LOCATION, bbox_inches='tight') # note: saved as .jpg
        return True

    # so messy...
    async def build_embed(self, ctx, price, ticker, ticker_info):
        """Builds the embed"""
        currency_name = " " + await bank.get_currency_name(ctx.guild)
        quote_type = ticker_info['quoteType']

        embed = discord.Embed(color=0x424549, title=const.BROKER_NAME,
        description="*\""+const.QUIPS[random.randint(0, len(const.QUIPS) - 1)]+"\"*")

        embed.add_field(name='Ticker', value=ticker_info['shortName'] +"\n"+ ticker, inline=True)
        embed.add_field(name='Current Price', value=str(price) + currency_name, inline=True)
        embed.add_field(name='Investment Type', value=quote_type, inline=True)

        # "Special" fields
        if quote_type == 'EQUITY':
            embed.add_field(name='Sector', value=ticker_info['sector'], inline=True)
            embed.add_field(name='Industry', value=ticker_info['industry'], inline=True)

            try:
                embed.add_field(name='Trailing P/E',
                value=f"{ticker_info['trailingPE']:.2f}",
                inline=True)
            except KeyError:
                embed.add_field(name='Trailing P/E',
                value="NaN",
                inline=True)

        elif quote_type == 'ETF':
            embed.add_field(name='Exchange', value=ticker_info['exchange'], inline=True)

            top_holdings = ''
            for key in range(0,3):
                top_holdings += f"""{ticker_info['holdings'][key]['symbol']}: 
                {ticker_info['holdings'][key]['holdingPercent'] * 100:.2f}%\n"""
            if top_holdings == '':
                top_holdings = 'NaN'
            embed.add_field(name='Top 3 Holdings', value = top_holdings, inline = True)

            embed.add_field(name='Assets Under Management', value = ticker_info['totalAssets'])

        embed.add_field(name='Open', value=ticker_info['open'],inline=True)
        embed.add_field(name='High', value=ticker_info['dayHigh'],inline=True)
        embed.add_field(name='Low', value=ticker_info['regularMarketDayLow'],inline=True)

        embed.add_field(name='52-Week Low', value=ticker_info['fiftyTwoWeekLow'],inline=True)
        embed.add_field(name='52-week high', value=ticker_info['fiftyTwoWeekHigh'] , inline=True)
        embed.add_field(name='Volume', value=ticker_info['volume'],inline=True)

        embed.set_footer(text='Enter 0 to cancel')

        return embed

    @commands.group()
    async def market(self, ctx):
        """Manage your Money! Manage your Life! Invest into the FUTURE!\n
        This collection of commands allow you to invest your hard earned money,
        into any publically traded company around the world!
        """

    @market.command(name="cleard", aliases=["cd"])
    async def clear_data(self, ctx):
        """Clear all dividend data"""
        await self.config.clear_all()
        


    @market.command(name="createacc", aliases=["ca", "create"])
    async def create_account(self, ctx, user_id: discord.Member = None):
        """Create an investment account for yourself!"""

        if user_id is None:
            user_id = ctx.author.id

        # Check if file exists
        if not os.path.isfile(const.DATA_FILE):
            with open(const.DATA_FILE, 'w+', encoding="utf8") as file:
                data = {
                            "portfolios": [
                                {
                                    "userId": user_id,
                                    "holdings": [
                                    ]
                                }
                            ]
                        }
                json.dump(data, file, indent=4)
                await ctx.send(f'Investment Account created for `{ctx.author.name}`!')
        else:
            with open(const.DATA_FILE, 'r+', encoding="utf8") as file:
                data = json.load(file)

                # anti-dupe
                for portfolio in data['portfolios']:
                    if portfolio['userId'] == user_id:
                        await ctx.send('Account already exists!')
                        file.close()
                        return

                data['portfolios'].append({
                    "userId": user_id,
                    "holdings": []
                })

                # rewrite file
                file.seek(0)
                file.truncate()
                json.dump(data, file, indent=4)
                await ctx.send(f'Investment Account created for `{ctx.author.name}`!')

    @market.command(name="sell")
    async def sell_stock(self, ctx, ticker: str, user_id: discord.Member = None):
        """Sell a user-specified amount of a stock"""
        ticker = ticker.upper()

        if user_id is None:
            user_id = ctx.author.id

        file =  open(const.DATA_FILE, 'r+', encoding="utf8")
        data = json.load(file)

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio is None:
            await ctx.send(const.ACCOUNT_NOT_FOUND_STR)
            return

        not_in_holding = True
        for holding in loaded_portfolio['holdings']:
            if ticker in holding:
                not_in_holding = False
                ticker_info = yf.Ticker(ticker).info
                price = ticker_info['regularMarketPrice']

                if price is None:
                    await ctx.send(const.INVALID_TICKER_STR)
                    return

                price = ceil(price * 100)

                embed = await self.build_embed(ctx, price, ticker, ticker_info)
                embed.add_field(name='How many shares would you like to sell?',
                value=f'You currently own {holding[ticker]} shares of {ticker} at {price} credits each.',
                inline=False)

                # sends image as attachment
                # thinking of just embeding the image via a link just so it looks prettier
                # upload image to imgur first or something idk
                await self.get_embed_chart(ticker)
                embed_file = discord.File(const.EMBED_LOCATION, filename=ticker + ".jpg")
                embed.set_image(url="attachment://image.jpg")

                sent_message = await ctx.send(file=embed_file, embed=embed)

                # await for input
                condition = MessagePredicate.greater(-1, ctx, None, ctx.author)
                try:
                    message = await ctx.bot.wait_for("message", check=condition, timeout=35.0)
                except asyncio.TimeoutError:
                    new_embed = discord.Embed(color=0xFF0000, title=const.BROKER_NAME, description=const.TRANSACTION_CANCELLED_STR)
                    await sent_message.edit(embed=new_embed)
                    return

                amount_to_sell = int(message.content)

                if 0 < amount_to_sell <= holding[ticker]:
                    holding[ticker] = holding[ticker] - amount_to_sell

                    new_embed = discord.Embed(color=0x00FF00, title=const.BROKER_NAME,
                    description=f'''You have sold {amount_to_sell}
                     shares of {ticker} at {price} credits each, 
                     for a total of {amount_to_sell * price} credits''')

                    old = await bank.get_balance(ctx.author)
                    new = await bank.deposit_credits(ctx.author, amount_to_sell * price)

                    new_embed.add_field(name='Previous Balance:', value=old)
                    new_embed.add_field(name='New Balance:', value=new)
                    await sent_message.edit(embed=new_embed)
                    break

                if amount_to_sell == 0:
                    new_embed = discord.Embed(color=0xFF0000, title=const.BROKER_NAME,
                    description=const.TRANSACTION_CANCELLED_STR)

                    await sent_message.edit(embed=new_embed)
                    break

                await ctx.send(f'You do not have that many shares of {ticker}!')

        if not_in_holding:
            await ctx.send(f'You do not own any shares of {ticker}!')
            file.close()
            return

        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=4)
        file.close()

    @market.command(name="buy")
    async def buy_stock(self, ctx, ticker: str, user_id: discord.Member = None):
        """
        Buy a stock! The specified ticker may require a suffix representing the exchange.
        By default, its assumed to be in the American stock exchanges. (NASDAQ, NYSE, AMEX)

        Toronto Stock Exchange (TSX) = .to
        TSX Venture Exchange (TSXV) = .v
        Shanghai Stock Exchange (SSE) = .ss
        Tokyo Stock Exchange (TYO) = .t
        Hong Kong Stock Exchange (HKSE) = .hk
        Shenzhen Stock Exchange (SZSE) = .sz

        Tickers for companies may be searched for on https://ca.finance.yahoo.com/
        Tickers are case-insensitive
        """
        ticker = ticker.upper()

        if not os.path.isfile(const.DATA_FILE):
            await ctx.send(const.ACCOUNT_NOT_FOUND_STR)
            return

        file =  open(const.DATA_FILE, 'r+', encoding="utf8")
        data = json.load(file)

        if user_id is None:
            user_id = ctx.author.id

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio is None:
            await ctx.send(const.ACCOUNT_NOT_FOUND_STR)
            return

        ticker_info = yf.Ticker(ticker).info # returns dict
        price = ticker_info['regularMarketPrice'] # may return None
        if price is None:
            await ctx.send(const.INVALID_TICKER_STR)
            return
        if ticker_info['quoteType'] == 'INDEX':
            await ctx.send(const.INVALID_TICKER_STR)
            return
        if ticker_info['quoteType'] == 'MUTUAL FUND':
            await ctx.send(const.INVALID_TICKER_STR)
            return

        price = ceil(price * 100)

        while True:
            # Get current price
            balance = await bank.get_balance(ctx.author)
            maximum_purchasable = floor(balance / price)

            if maximum_purchasable == 0:
                await ctx.send(const.POOR_STR)
                return

            # build & send embed
            embed = await self.build_embed(ctx, price, ticker, ticker_info)

            embed.add_field(name='How many shares would you like to buy?',
            value=f'You can buy up to {maximum_purchasable} shares of {ticker}', inline=False)

            # No Chart? then it doesn't exist
            if not await self.get_embed_chart(ticker):
                await ctx.send(const.INVALID_TICKER_STR)
                return
            embed_file = discord.File(const.EMBED_LOCATION, filename=ticker + ".jpg")
            embed.set_image(url="attachment://image.jpg")

            sent_message = await ctx.send(file=embed_file, embed=embed)

            condition = MessagePredicate.greater(-1, ctx, None, ctx.author)

            try:
                message = await ctx.bot.wait_for("message", check=condition, timeout=35.0)
            except asyncio.TimeoutError:
                new_embed = discord.Embed(color=0xFF0000, title=const.BROKER_NAME, description=const.TRANSACTION_CANCELLED_STR)
                await sent_message.edit(embed=new_embed)
                return
            amount_to_buy = int(message.content)

            if 0 < amount_to_buy <= maximum_purchasable:
                break

            if amount_to_buy == 0:
                new_embed = discord.Embed(color=0xFF0000, title=const.BROKER_NAME,
                description=const.TRANSACTION_CANCELLED_STR)
                await sent_message.edit(embed=new_embed)
                file.close()
                return

        new_embed = discord.Embed(color=0x00FF00, title=const.BROKER_NAME,
        description='Shares Purchased!')
        await sent_message.edit(embed=new_embed)
        await bank.withdraw_credits(ctx.author, amount_to_buy * price)

        # Dividend check
        await self.dividend_check(ticker_info, ticker, amount_to_buy, user_id)

        # add stock to portfolio
        # Could add more details to each holdings, like average price etc.
        owned = False
        for holding in loaded_portfolio['holdings']:
            if ticker in holding:
                holding[ticker] += amount_to_buy
                owned = True
                break

        if not owned:
            loaded_portfolio['holdings'].append({
                ticker: amount_to_buy
            })

        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=4)
        file.close()

    @market.command(name="holdings")
    async def list_holdings(self, ctx, user_id: discord.Member = None):
        """Lists all of your stocks and everything else that is in your portfolio"""
        file =  open(const.DATA_FILE, 'r', encoding="utf8")
        data = json.load(file)
        file.close()

        if user_id is None:
            user_id = ctx.author.id

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio is None:
            await ctx.send(const.ACCOUNT_NOT_FOUND_STR)
            return

        if len(loaded_portfolio['holdings']) == 0:
            await ctx.send('You do not own any stocks!')
            return

        port_value = 0

        msg = 'You own the following stocks:\n ```css\n'

        for holding in loaded_portfolio['holdings']:
            for ticker in holding:
                msg += f'[{holding[ticker]}] shares of [{ticker}]\n'
                port_value += holding[ticker]*ceil(yf.Ticker(ticker).info['regularMarketPrice']*100)

        port_value = str(port_value) + " " + await bank.get_currency_name(ctx.guild)
        msg += f'\n your portfolio\'s total value is: {port_value}!```'

        await ctx.send(msg)

    # chart
    @market.command(name="chart")
    async def get_chart(self, ctx, ticker: str, period_str = '1d', interval_str = '5m'):
        """Gets a chart of a stock, period and interval can be specified"""
        await self.get_embed_chart(ticker, period_str, interval_str)
        await ctx.send(file = discord.File(const.EMBED_LOCATION, filename = ticker + ".jpg"))

    # Simple Information
    @market.command(name="info")
    async def get_info(self, ctx, ticker: str):
        """Gets information about a particular stock"""
        ticker = ticker.upper()
        info = yf.Ticker(ticker).info
        print(info)

        embed = await self.build_embed(ctx, ceil(info['regularMarketPrice'] * 100), ticker, info)
        embed.set_footer(text=f'{ticker} - {info['shortName']}')
        try:
            summary = info['longBusinessSummary']
            summary = (summary[:1021] + '...') if len(summary) > 1021 else summary
            embed.add_field(name=f'About {ticker}', value=summary, inline=False)
        except KeyError:
            embed.add_field(name=f'About {ticker}',
            value=f'No information found for ticker {ticker}', inline=False)

        await ctx.send(embed=embed)
