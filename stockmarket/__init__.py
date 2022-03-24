from .market import Market


def setup(bot):
    bot.add_cog(Market(bot))