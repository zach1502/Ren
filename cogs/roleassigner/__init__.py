"""roleassigner module.

Assign roles to certain guild members.
"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .roleassigner import RoleAssigner

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def setup(bot: Red):
    """Add the cog to the bot."""
    bot.add_cog(RoleAssigner(bot))
