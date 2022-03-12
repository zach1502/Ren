from math import floor, ceil
import random
import json
import os
import matplotlib.pyplot as plt 
import yfinance as yf # pip install yfinance
import asyncio
import discord

from redbot.core import bank, commands
from redbot.core.utils.predicates import MessagePredicate

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

    # Gonna move these all to a different file later
    DATA_FILE = 'cogs\\stockmarket\\portfolios.json'
    EMBED_LOCATION = 'cogs\\stockmarket\\chart.jpg'
    TRANSACTION_CANCELLED_STR = 'Transaction cancelled!'
    INVALID_TICKER_STR = 'Invalid ticker symbol!'
    POOR_STR = 'You do not have enough money to buy this stock!'
    ACCOUNT_NOT_FOUND_STR = 'No account found! Please create an account using `renmarket createacc`.' #.format(get prefix somehow)
    QUIPS = ['Ready to Donate your money to Wall Street I see?',
    'AAAAAAAAAAND IT\'S GONE!', 
    'Diamond Hands! :raised_hands: :gem:', 
    'Look, I swear I have a Securities License!',
    'I\'m maybe not a real broker, but I can help you with that!',
    '$TSLA is the best stock in the world!',
    'Wow, did you learn that from r/wallstreetbets?',
    'Stocks are the only thing I would willingly buy high and sell low',
    'Pssst, I have insider information on this stock!',
    'Nothing brings me more joy than receiving dividends!',
    'I found out that I can manipulate stock market. Whatever I bought, it went red.',
    'The best way to earn a million dollars is to invest 10 million',
    'Let\'s talk about my retirement plan!',
    '100% Not a pyramid scheme!',
    'Technical analysis is the Astrology of the stock market!',
    'Look! the "Evergreen Forest" Formation is forming in the charts!',
    'BUY BUY BUY!',
    'SELL SELL SELL!',
    'Buying and holding for the long run is the best strategy!',
    'Oh! Tell me more about your NFT collection!',
    'Something about THIS stocks feels good!',
    'Started from the bottom now we\'re here!',
    'Learn to Invest!',
    'short my stock, I shorten your life! :knife: :knife: :knife:',
    'Value or Growth stocks? :thinking:',
    'I still don\'t how the market works, and at this point I\'m afraid to ask.',
    'I am a financial genious!',
    'Since I own this stock, you should buy it!',
    'The more you invest, the more I will earn!',
    'By the time you\'re old enough to retire, you\'ll have more money than you think!',
    'You\'re poorer than you think! ScotiaBank!',
    'APES TOGETHER STRONG',
    'Welcome back summoner!',
    'You can\'t find great value even if you were in a Walmart!',
    'Donate money to your rich local broker today',
    'Do you know why the European stock markets are sliding down?, Greece.',
    'How to be rich. Step 1: Take out student loans, Step 2: Invest in stocks, Step 3: Profit!',
    '$GME go BRRRRRRRRRRRRRRRRRRRRRR'
    ]

    def __init__(self, bot):
        self.bot = bot

    async def load_portfolio(self, data, user_id):
        loaded_portfolio = None

        for portfolio in data['portfolios']:
            if portfolio['userId'] == user_id:
                loaded_portfolio = portfolio
                return loaded_portfolio
        
        return None

    async def get_embed_chart(self, ticker, period_str = '1d', interval_str = '5m'):
        plt.clf()
        ticker = ticker.upper()
        # Get the data
        data = yf.download(ticker, period = period_str, interval = interval_str)

        # print(data) #debug

        if len(data['Close']) == 0:
            return False

        for i in range(0, len(data['Close'])):
            data['Close'][i] *= 100

        # Plot the data using the close data
        data['Close'].plot(color='red' if (data['Close'][0] - data['Close'][-1] > 0) else 'green')

        plt.title(ticker)
        plt.ylabel('Price')
        plt.grid()

        #convert to webp????
        plt.savefig(self.EMBED_LOCATION, bbox_inches='tight') # note: saved as .jpg
        return True

    async def build_embed(self, ctx, price, ticker, ticker_info):
        currency_name = " " + await bank.get_currency_name(ctx.guild)

        embed = discord.Embed(color=0x424549, title='Ren\'s Brokerage', description="*\""+self.QUIPS[random.randint(0, len(self.QUIPS) - 1)]+"\"*")
        embed.add_field(name='Ticker', value=ticker_info['shortName'] +"\n"+ ticker, inline=True)
        embed.add_field(name='Current Price', value=str(price) + currency_name, inline=True)
        embed.add_field(name='Investment Type', value=ticker_info['quoteType'], inline=True)

        if ticker_info['quoteType'] == 'EQUITY':
            embed.add_field(name='Sector', value=ticker_info['sector'], inline=True)
            embed.add_field(name='Industry', value=ticker_info['industry'], inline=True)
            embed.add_field(name='Trailing P/E', value='%.2f' % ticker_info['trailingPE'] , inline=True)

        elif ticker_info['quoteType'] == 'ETF':
            embed.add_field(name='Exchange', value=ticker_info['exchange'], inline=True)

            top_holdings = ''
            for key in range(0,3):
                top_holdings += ticker_info['holdings'][key]['symbol'] + ': ' + '%.2f%%' % (ticker_info['holdings'][key]['holdingPercent'] * 100) + '\n'
            if top_holdings == '':
                top_holdings = 'NaN'
            embed.add_field(name='Top 3 Holdings', value = top_holdings, inline = True)

            embed.add_field(name='Assets Under Management', value = ticker_info['totalAssets'])

        elif ticker_info['quoteType'] == 'MUTUALFUND':
            embed.add_field(name='Exchange', value=ticker_info['exchange'], inline=True)
            top_holdings = ''
            for key in range(0,3):
                top_holdings += ticker_info['holdings'][key]['symbol'] + ': ' + '%.2f%%' % (ticker_info['holdings'][key]['holdingPercent'] * 100) + '\n'
            if top_holdings == '':
                top_holdings = 'NaN'
            embed.add_field(name='Top 3 Holdings', value = top_holdings, inline = True)
            embed.add_field(name='Average Volume', value = ticker_info['averageVolume'], inline = True)
        


        embed.add_field(name='Open', value=ticker_info['open'],inline=True)
        embed.add_field(name='High', value=ticker_info['dayHigh'],inline=True)
        embed.add_field(name='Low', value=ticker_info['regularMarketDayLow'],inline=True)

        embed.add_field(name='52-Week Low', value=ticker_info['fiftyTwoWeekLow'],inline=True)
        embed.add_field(name='52-week high', value=ticker_info['fiftyTwoWeekHigh'] , inline=True)
        embed.add_field(name='Volume', value=ticker_info['volume'],inline=True)

        embed.set_footer(text='Enter 0 to cancel')

        return embed

    @commands.group(no_pm=True)
    async def market(self, ctx):
        #grouping
        pass

    @market.command(name="createacc", aliases=["ca", "create"])
    async def create_account(self, ctx, user_id: discord.Member = None):
        """Create an investment account for yourself.. And give me all your money!"""
        if user_id is None:
            user_id = ctx.author.id

        # Check if file exists
        if not os.path.isfile(self.DATA_FILE):
            f = open(self.DATA_FILE, 'w+')
            data = { 
                        "portfolios": [
                            {
                                "userId": user_id,
                                "holdings": [
                                ]
                            }
                        ]
                    }
            json.dump(data, f, indent=4)
            await ctx.send('Investment Account created for `{}`!'.format(ctx.author.name))
            return
        else:
            f = open(self.DATA_FILE, 'r+')

        data = json.load(f)

        # anti-dupe
        for portfolio in data['portfolios']:
            if portfolio['userId'] == user_id:
                await ctx.send('Account already exists!')
                f.close()
                return

        # add account
        data['portfolios'].append({
            "userId": user_id,
            "holdings": []
        })

        # rewrite file
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=4)
        await ctx.send('Investment Account created for `{}`!'.format(ctx.author.name))

    @market.command(name="sell")
    async def sell_stock(self, ctx, ticker: str, user_id: discord.Member = None):
        ticker = ticker.upper()
        f = open(self.DATA_FILE, 'r+')
        data = json.load(f)

        if user_id is None:
            user_id = ctx.author.id

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio == None:
            await ctx.send(self.ACCOUNT_NOT_FOUND_STR)
            return

        not_in_holding = True
        for holding in loaded_portfolio['holdings']:
            if ticker in holding:
                not_in_holding = False
                ticker_info=yf.Ticker(ticker).info
                price = ticker_info['regularMarketPrice']

                if price is None:
                    await ctx.send(self.INVALID_TICKER_STR)
                    return

                price = ceil(price * 100)

                embed = await self.build_embed(ctx, price, ticker, ticker_info)
                embed.add_field(name='How many shares would you like to sell?', value='You currently own {} shares of {} at {} credits each.'.format(holding[ticker], ticker, price), inline=False)

                # sends image as attachment
                # thinking of just embeding the image via a link just so it looks prettier
                # upload image to imgur first or something idk
                await self.get_embed_chart(ticker) 
                file = discord.File(self.EMBED_LOCATION, filename=ticker + ".jpg")
                embed.set_image(url="attachment://image.jpg")

                await ctx.send(file=file, embed=embed)
                # await for input
                condition = MessagePredicate.positive(ctx, None, ctx.author)
                try:
                    message = await ctx.bot.wait_for("message", check=condition, timeout=35.0)
                except asyncio.TimeoutError:
                    await ctx.send(self.TRANSACTION_CANCELLED_STR)
                    return

                amount_to_sell = int(message.content)

                if 0 < amount_to_sell <= holding[ticker]:
                    holding[ticker] = holding[ticker] - amount_to_sell

                    await ctx.send('You have sold {} shares of {} at {} credits each, for a total of {} credits' .format(amount_to_sell, ticker, price, amount_to_sell * price))
                    old = await bank.get_balance(ctx.author)
                    new = await bank.deposit_credits(ctx.author, amount_to_sell * price)
                    await ctx.send('From:`{}` credits!, To: `{}` credits!'.format(old, new))
                    break

                if amount_to_sell == 0:
                    await ctx.send(self.TRANSACTION_CANCELLED_STR)
                    break

                await ctx.send('You do not have that many shares!')

        
        if not_in_holding:
            await ctx.send('You do not own any shares of {}!'.format(ticker))
            f.close()
            return

        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=4)
        f.close()

    @market.command(name="buy")
    async def buy_stock(self, ctx, ticker: str, user_id: discord.Member = None):
        ticker = ticker.upper()

        if not os.path.isfile(self.DATA_FILE):
            await ctx.send(self.ACCOUNT_NOT_FOUND_STR)
            return

        f = open(self.DATA_FILE, 'r+')
        data = json.load(f)

        if user_id is None:
            user_id = ctx.author.id

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio == None:
            await ctx.send(self.ACCOUNT_NOT_FOUND_STR)

            return

        ticker_info = yf.Ticker(ticker).info # returns dict
        price = ticker_info['regularMarketPrice'] # may return None
        if price is None:
            await ctx.send(self.INVALID_TICKER_STR)
            return

        price = ceil(price * 100)

        while(True):
            # Get current price
            balance = await bank.get_balance(ctx.author)
            maximum_purchasable = floor(balance / price)

            if(maximum_purchasable == 0):
                await ctx.send(self.POOR_STR)
                return

            # build & send embed
            embed = await self.build_embed(ctx, price, ticker, ticker_info)
            embed.add_field(name='How many shares would you like to buy?', value='You can buy up to {} shares of {}'.format(maximum_purchasable, ticker), inline=False)

            # No Chart? then it doesn't exist
            if not await self.get_embed_chart(ticker):
                await ctx.send(self.INVALID_TICKER_STR)
                return
            file = discord.File(self.EMBED_LOCATION, filename=ticker + ".jpg")
            embed.set_image(url="attachment://image.jpg")
            
            await ctx.send(file=file, embed=embed)
            
            condition = MessagePredicate.positive(ctx, None, ctx.author)
            try:
                message = await ctx.bot.wait_for("message", check=condition, timeout=35.0)
            except asyncio.TimeoutError:
                await ctx.send(self.TRANSACTION_CANCELLED_STR)
                return

            amount_to_buy = int(message.content)

            if 0 < amount_to_buy <= maximum_purchasable:
                break

            if amount_to_buy == 0:
                await ctx.send(self.TRANSACTION_CANCELLED_STR)
                f.close()
                return

        await ctx.send('Shares Purchased!')
        await bank.withdraw_credits(ctx.author, amount_to_buy * price)

        #REMOVE CREDITS

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

        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=4)
        f.close()

    @market.command(name="holdings")
    async def list_holdings(self, ctx, user_id: discord.Member = None):
        f = open(self.DATA_FILE, 'r')
        data = json.load(f)
        f.close()

        if user_id is None:
            user_id = ctx.author.id

        loaded_portfolio = await self.load_portfolio(data, user_id)
        if loaded_portfolio == None:
            await ctx.send(self.ACCOUNT_NOT_FOUND_STR)
            return

        if len(loaded_portfolio['holdings']) == 0:
            await ctx.send('You do not own any stocks!')
            return

        port_value = 0

        msg = 'You own the following stocks:\n ```css\n'

        for holding in loaded_portfolio['holdings']:
            for ticker in holding:
                msg += '[{}] shares of [{}]\n'.format(holding[ticker], ticker)
                port_value += holding[ticker] * ceil(yf.Ticker(ticker).info['regularMarketPrice'] * 100)
        
        port_value = str(port_value) + " " + await bank.get_currency_name(ctx.guild)
        msg += '\n your portfolio\'s total value is: {}!```'.format(port_value) 

        await ctx.send(msg)

    # chart
    @market.command(name="chart")
    async def get_chart(self, ctx, ticker: str, period_str = '1d', interval_str = '5m'):
        await self.get_embed_chart(ticker, period_str, interval_str)
        await ctx.send(file = discord.File(self.EMBED_LOCATION, filename = ticker + ".jpg"))

    # Simple Information
    @market.command(name="info")
    async def get_info(self, ctx, ticker: str):
        ticker = ticker.upper()
        info = yf.Ticker(ticker).info
        try:
            msg = info['longBusinessSummary']
        except KeyError:
            msg = 'No information found for ticker {}'.format(ticker)
        await ctx.send(msg)
        msg = ''

        for key in info:
            msg += "{}: {}\n".format(key, info[key])

            if msg.count('\n') > 20:
                await ctx.send(msg)
                msg = ''

        await ctx.send(msg)

