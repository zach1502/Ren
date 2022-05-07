""" Here is the Module Docstring"""
from math import floor, ceil
import random
import json
import os
import asyncio
import time
import datetime
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
# 3. Events (i.e. Dividends and splits) are WIP and not tested
# 4. Buy & Sell functions probably can be simplified somehow
# 5. Time is saved oddly, think its only because of the api but need to figure out why
# 6. buy/sell with the full company name instead of tickers

class Market(commands.Cog):
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

    member_data = {
        "claimed_events": [],
        "holdings": []
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=835888251, force_registration=True)
        self.config.register_member(**self.member_data)
        self.enable_bg_loop() # uncomment to enable dividends. WIP

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
            await asyncio.sleep(10) # once a day will suffice 86400

    async def check_events(self):
        """Checks if any events are due and pays them out"""

        # Surely there's something better than this junk
        all_member_data = await self.config.all_members(guild=None)
        for singular_guild_id in all_member_data:
            for singular_member_id in all_member_data[singular_guild_id]:
                for holding in all_member_data[singular_guild_id][singular_member_id]['holdings']:

                    # need to put into an async await function. Takes too long and blocks the thread
                    ticker = holding['ticker']
                    # actions list
                    actions = yf.Ticker(ticker).actions
                    # last action date
                    date = str(actions.index[-1])[:-9]
                    # convert date time to unix time
                    most_recent_unix = time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())
                    # current unix time
                    current_unix = time.time()

                    print("attempting to deposit dividends")
                    # await bank.deposit_credits(singular_member_id, 100)
                    print("YES!")
                    
                    guild_object = self.bot.get_guild(singular_guild_id)
                    member_object = await guild_object.fetch_member(singular_member_id)
                    # docs say returns Discord.Member, but it doesnt???
                    # so it hangs right below
                    await bank.deposit_credits(member_object, dividend_due_per_share * shares_owned)

                    # check if ticker and time is in claimed events
                    try:
                        print(all_member_data[singular_guild_id][singular_member_id]['claimed_events']) # this part causes it to crash
                        for all_tickers in all_member_data[singular_guild_id][singular_member_id]['claimed_events']:
                            if most_recent_unix not in all_tickers[ticker] and current_unix > most_recent_unix > holding['initial DOP']:
                                # if not, add it to the list
                                all_member_data[singular_guild_id][singular_member_id]['claimed_events'].append({
                                    ticker: [most_recent_unix]
                                })

                                # pay out the dividend and/or split
                                dividend_due_per_share = actions.iloc[-1][0]
                                split_due_per_share = actions.iloc[-1][1]

                                # order doesn't matter since companies always try to avoid paying out dividends/splits at the same time
                                # pay out the dividend
                                shares_owned = holding['amount']

                                # pay dividend
                                if dividend_due_per_share > 0:
                                    guild_object = self.bot.get_guild(int(singular_guild_id))
                                    member_object = guild_object.get_member(int(singular_member_id))
                                    await bank.deposit_credits(member_object, dividend_due_per_share * shares_owned)
                                    await singular_member_id.send(f"you have received a dividend of ${dividend_due_per_share * shares_owned} from {ticker}!")
                                # pay split
                                if split_due_per_share > 0:
                                    holding['amount'] += holding['amount'] * split_due_per_share
                                    await singular_member_id.send(f"you have received a {split_due_per_share} split from {ticker}!")

                    except Exception as e: # should be catching a Key Error
                        print(e)
                        print("in key error")
                        continue


    @commands.group()
    async def market(self, ctx):
        """Manage your Money! Manage your Life! Invest into the FUTURE!\n
        This collection of commands allow you to invest your hard earned money,
        into any publicly traded company around the world! #GetRichSlow
        """

    @market.command(name="sell")
    async def sell_stock(self, ctx, ticker: str, user_id: discord.Member = None):
        """Sell a user-specified amount of a stock"""
        ticker = ticker.upper()

        if user_id is None:
            user_id = ctx.author.id

        not_in_holding = True

        async with self.config.member(ctx.author).holdings() as holdings:
            for holding in holdings:
                if holding['ticker'] == ticker:
                    amount_owned = holding['amount']
                    not_in_holding = False
                    ticker_info = yf.Ticker(ticker).info
                    price = ticker_info['regularMarketPrice']

                    if price is None:
                        await ctx.send(const.INVALID_TICKER_STR)
                        return

                    price = ceil(price * 100)

                    embed = await self.build_embed(ctx, price, ticker, ticker_info)
                    embed.add_field(name='How many shares would you like to sell?',
                    value=f'You currently own {amount_owned} shares of {ticker} at {price} credits each.',
                    inline=False)

                    # sends image as attachment
                    # thinking of just embeding the image via a link just so it looks prettier
                    # upload image to imgur first or something idk
                    await self.get_embed_chart(ticker)
                    embed_file = discord.File(const.EMBED_LOCATION, filename=ticker + ".jpg")
                    embed.set_image(url="attachment://image.jpg")

                    sent_message = await ctx.send(file=embed_file, embed=embed)

                    # await for input
                    condition = MessagePredicate.greater(0, ctx, None, ctx.author)
                    try:
                        message = await ctx.bot.wait_for("message", check=condition, timeout=35.0)
                    except asyncio.TimeoutError:
                        new_embed = discord.Embed(color=0xFF0000, title=const.BROKER_NAME, description=const.TRANSACTION_CANCELLED_STR)
                        await sent_message.edit(embed=new_embed)
                        return

                    amount_to_sell = int(message.content)

                    if 0 < amount_to_sell <= holding['amount']:
                        if amount_to_sell == holding['amount']:
                            holdings.remove(holding)

                        holding['amount'] -= amount_to_sell

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
            return


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

        if user_id is None:
            user_id = ctx.author.id

        start = time.time()
        ticker_info = yf.Ticker(ticker).info # returns dict
        end = time.time()

        print(f'getting yf data took {end - start} seconds')
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

        # Get current price
        balance = await bank.get_balance(ctx.author)
        maximum_purchasable = floor(balance / price)

        if maximum_purchasable == 0:
            await ctx.send(const.POOR_STR)
            return

        while True:
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

            condition = MessagePredicate.greater(0, ctx, None, ctx.author)

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
                return

        new_embed = discord.Embed(color=0x00FF00, title=const.BROKER_NAME,
        description='Shares Purchased!')
        await sent_message.edit(embed=new_embed)
        await bank.withdraw_credits(ctx.author, amount_to_buy * price)

        # add stock to portfolio
        # Could add more details to each holdings, like average price etc.
        async with self.config.member(ctx.author).holdings() as holdings:
            for holding in holdings:
                if holding['ticker'] == ticker:
                    holding['amount'] += amount_to_buy
                    return

            holdings.append({'ticker': ticker, 'amount': amount_to_buy, 'initial DOP': time.time()})
        

    @market.command(name="holdings")
    async def list_holdings(self, ctx, user_id: discord.Member = None):
        """Lists all of your stocks and everything else that is in your portfolio"""

        print(user_id)
        if user_id is None:
            user_id = ctx.author.id

        async with self.config.member(ctx.author).holdings() as holdings:
            if not holdings:
                await ctx.send(f'{ctx.author.mention} you do not own any shares!')
                return

            port_value = 0
            msg = 'You own the following stocks:\n ```css\n'

            print(holdings)
            
            for holding in holdings:
                ticker = holding['ticker']
                amount = holding['amount']
                msg += f'[{amount}] shares of [{ticker}]\n'
                port_value += amount * ceil(yf.Ticker(ticker).info['regularMarketPrice'] * 100)

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
        shortName = info['shortName']
        embed.set_footer(text=f'{ticker} - {shortName}')
        try:
            summary = info['longBusinessSummary']
            summary = (summary[:1021] + '...') if len(summary) > 1021 else summary
            embed.add_field(name=f'About {ticker}', value=summary, inline=False)
        except KeyError:
            embed.add_field(name=f'About {ticker}',
            value=f'No information found for ticker {ticker}', inline=False)

        await ctx.send(embed=embed)

    # Simple Information
    @market.command(name="events")
    async def get_sinfo(self, ctx, ticker: str):
        """Gets information about a particular stock"""
        ticker = ticker.upper()

        actions = yf.Ticker(ticker).actions

        msg = ""
        for key in actions:
            msg += f'{key}: {actions[key]}\n'
        print(actions)

        # check last row of dataframe
        last_row = actions.iloc[-1]

        # get the first column
        date = str(actions.index[-1])[:-9]

        print((actions.iloc[-1])[0])

        print("date of last row ")
        print(date)

        print("this is the last row ")
        print(last_row)

        # convert datetime to unix timestamp
        current_time = time.time()
        
        # convert current time to datetime
        current_time = datetime.datetime.fromtimestamp(current_time)
        print("currenttime = ")
        print(current_time)

        most_recent_unix = time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())
        await ctx.send(most_recent_unix)

        await ctx.send(msg)

        print(await self.config.all_users())

        print(await self.config.all_members(guild=None))

    async def get_embed_chart(self, ticker, period_str = '1d', interval_str = '5m'):
        """Gets the chart of the requested stock"""
        plt.clf()
        ticker = ticker.upper()
        # Get the data.. takes like 0.2s
        data = yf.download(ticker, period = period_str, interval = interval_str)

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