import os
from discord.ext import commands
from .utils.dataIO import fileIO
from difflib import SequenceMatcher
import aiohttp
import asyncio

class Games:
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/games/games.json'

    def match(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    async def listener(self, before, after):
        before_game = str(before.game)
        try:
            after_game = str(after.game)
        except TypeError:
            after_game = 'None'
        server = after.server

        if not after.bot:
            if after_game != 'None' and after_game != '':
                if before_game != after_game:
                    data = fileIO(self.data_file, 'load')
                    if server.id not in data:
                        data[server.id] = {}
                        data[server.id]['GAMES'] = {}
                    game_match = ''
                    for game in data[server.id]['GAMES']:
                        if self.match(str(game).upper(), after_game.upper()) > 0.89 and self.match(str(game).upper(), after_game.upper()) < 1.0:
                            game_match = game
                    if game_match in data[server.id]['GAMES']:
                        data[server.id]['GAMES'][game_match]['PLAYED'] += 1
                    elif after_game not in data[server.id]['GAMES']:
                        data[server.id]['GAMES'][after_game] = {}
                        data[server.id]['GAMES'][after_game]['PLAYED'] = 1
                        data[server.id]['GAMES'][after_game]['GAME'] = after_game
                    else:
                        data[server.id]['GAMES'][after_game]['PLAYED'] += 1
                    fileIO(self.data_file, 'save', data)

    @commands.command(pass_context=True, no_pm=True, name='games')
    async def _games(self, context):
        """Shows top 10 most popular games on this server."""
        server = context.message.server
        data = fileIO(self.data_file, 'load')
        if server.id in data:
            data = data[server.id]['GAMES']
            games_played = sorted(data, key=lambda x: (data[x]['PLAYED']), reverse=True)
            message = '```Most popular games played on {}\n\n'.format(server.name)
            for i, game in enumerate(games_played, 1):
                if i > 10:
                    break
                message+='{:<5}{:<10}\n'.format(i, game)
            message+='```'
            await self.bot.say(message + "\nFull games list at https://ren.injabie3.moe/games")

def check_folder():
    if not os.path.exists('data/games'):
        print('Creating data/games folder...')
        os.makedirs('data/games')

def check_file():
    data = {}
    f = 'data/games/games.json'
    if not fileIO(f, 'check'):
        print('Creating default games.json...')
        fileIO(f, 'save', data)

def setup(bot):
    check_folder()
    check_file()
    n = Games(bot)
    bot.add_listener(n.listener, 'on_member_update')
    bot.add_cog(n)
