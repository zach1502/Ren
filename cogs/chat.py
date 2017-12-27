import discord
from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO
import asyncio
import os
import requests
import json

#Global Vars
user = "user"
key = "key"
"""Get your own id and key at https://cleverbot.io/keys."""

class chat:
    """An attempt to use chatbot.io, based of 26 cogs' cleverbot
    but it used cleverbot api which went pay to play"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/chat/settings.json")
        self.instances = {}

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    async def chat(self, ctx, *, message):
        """Talk with cleverbot"""
        author = ctx.message.author
        channel = ctx.message.channel
        text = ctx.message.clean_content
        result = await self.get_response(author, text, message)
        await self.bot.say(result)

    @chat.command()
    @checks.is_owner()
    async def toggle(self):
    	"""Turn chatbot on or off"""
    	self.settings["TOGGLE"] = not self.settings["TOGGLE"]
    	if self.settings["TOGGLE"]:
    		await self.bot.say("I will respond to pings.")
    	else:
    		await self.bot.say("I won't reply anymore.")

    @chat.command()
    @checks.is_owner()
    async def user(self, user: str):
    	"""Sets user token for cleverbot.io"""
    	self.settings["chatbot_id"] = user
    	self.settings.pop("user", None)
    	dataIO.save_json("data/chat/settings.json", self.settings)
    	await self.bot.say("User ID set")

    @chat.command()
    @checks.is_owner()
    async def apikey(self, key: str):
    	"""Sets api key for cleverbot.io"""
    	self.settings["chatbot_api_key"] = key
    	self.settings.pop("key", None)
    	dataIO.save_json("data/chat/settings.json", self.settings)
    	await self.bot.say("API key set")

    async def get_response(self, author, text, message):
        """Sends a formatted message to cleverbot and returns a response"""
        user = self.settings["chatbot_id"]
        key = self.settings["chatbot_api_key"]
        r=json.loads(requests.post('https://cleverbot.io/1.0/ask',json={'user':user,'key':key,'nick':'you', 'text':text}).text)
        if r['status'] == 'success':
        	return r['response']
        else:
        	return 'Sorry I cannot talk at the moment try again later'

    async def on_message(self, message):
    	"""Takes user input and formats it into a proper message for the bot"""
    	if not self.settings["TOGGLE"] or message.server is None:
    		return

    	if not self.bot.user_allowed(message):
    		return
    	author = message.author
    	channel = message.channel
    	if message.author.id != self.bot.user.id:
    		to_strip = "@" + author.server.me.display_name + " "
    		text = message.clean_content
    		if not text.startswith(to_strip):
    			return
    		text = text.replace(to_strip, "", 1)
    		await self.bot.send_typing(channel)
    		response = await self.get_response(author, text, message)
    		await self.bot.send_message(channel, response)

#Data folder for first time
def check_folders():
    if not os.path.exists("data/chat"):
        print("Creating data/chat folder...")
        os.makedirs("data/chat")

#Default data for first time
def check_files():
    f = "data/chat/settings.json"
    data = {"TOGGLE" : True}
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, data)

def setup(bot):
	check_folders()
	check_files()
	n = chat(bot)
	bot.add_cog(n)