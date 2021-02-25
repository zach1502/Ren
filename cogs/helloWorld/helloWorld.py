from redbot.core import commands
import discord
from discord_slash import cog_ext, SlashContext

class HelloWorld(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="helloworld")
    async def _test(self, ctx: SlashContext):
        """Hello world, a programmer's favourite statement!"""
        embed = discord.Embed(title="Look at this embed")
        await ctx.send(content="Hello world!", embeds=[embed])
