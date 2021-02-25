from redbot.core.bot import Red
from .helloWorld import HelloWorld


def setup(bot: Red):
    bot.add_cog(HelloWorld(bot))
