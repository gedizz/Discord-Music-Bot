import discord
from discord.ext import commands, tasks
import creds
from Player import Player

# init player
bot = commands.Bot(command_prefix='!', help_command=None)
guild_dict = {}


###########################
###  Utility Functions  ###
###########################



####################
###  Task Loops  ###
####################


##############
##  Events  ##
##############
@bot.event
async def on_ready():
    print("Bot is ready")
    for guild in bot.guilds:
        guild_dict[guild] = Player(guild)


################
##  Commands  ##
################
@bot.command()
async def play(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    guild_dict[ctx.guild].play_audio("hotel.mp3", voice_client)


@bot.command()
async def join(ctx):
    channel = ctx.author.voice.channel
    await channel.connect()


@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()


# Run bot
bot.run(creds.api_key)
