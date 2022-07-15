import time
import discord
from discord.ext import commands, tasks
import creds
from rustplus import RustSocket, FCMListener, CommandOptions, Command
import asyncio
from PIL import Image
import json
import datetime
import time

#CONSTANTS
bot = commands.Bot(command_prefix='!', help_command=None)
STEAMID = 76561198040853461 # my steam id -- never changes
PLAYERTOKEN = -432760157    # my player token. Might change

ENTITIES = {
    "sams": [14395633],
    "turrets": [14764611, 14995747],
}

#options = CommandOptions(prefix="!") # Use whatever prefix you want here
rust_socket = RustSocket("154.16.128.35", "28017", STEAMID, PLAYERTOKEN, raise_ratelimit_exception=False)

###########################
###  Utility Functions  ###
###########################



####################
###  Task Loops  ###
####################
# @tasks.loop(seconds=3.0)
# async def guild_tasks():
#     for guild in bot.guilds:
#
#         if guild.id == 961048740754505728:
#             await loadchat(guild)




##############
##  Events  ##
##############
@bot.event
async def on_ready():
    num_guilds = len(bot.guilds)
    print(f"Rust+ Bot Online")
    time.sleep(2)
    #guild_tasks.start()
    await bot.change_presence(activity=discord.Game(name="Rust+ | !rust"))



# handles all messages from users. Will force all commands to be lowercase
@bot.event
async def on_message(message):
    # make list to find first word in message.content and make ONLY that lowercase
    content_list = message.content.split()
    for word in content_list:
        if word == content_list[0]:
            message.content = message.content.replace(word, word.lower())

    await bot.process_commands(message)

    if message.channel.name == "team-chat" and not message.author.bot:
        username = "" if message.author.name == "[HARR] Walton Towers" else message.author.name
        print("team chat")
        print(username)
        await rust_socket.connect()
        await rust_socket.send_team_message(username + ": " + message.content)
        await rust_socket.disconnect()
    else:
        print("Not team chat or is a bot")
    #print(message.created_at)
    presentDate = datetime.datetime.now()
    unix_timestamp = datetime.datetime.timestamp(presentDate)
    #print(unix_timestamp)


################
##  Commands  ##
################



with open("rustplus.py.config.json", "r") as input_file:
    fcm_details = json.load(input_file)


class FCM(FCMListener):

    def on_notification(self, obj, notification, data_message):
        print(notification)


FCM(fcm_details).start()


@bot.command()
async def sams(ctx):
    await rust_socket.connect()
    sams_list = ENTITIES["sams"]

    for sam in sams_list:
        sam_info = await rust_socket.get_entity_info(sam)
        if sam_info.value:
            await rust_socket.turn_off_smart_switch(sam)
            await ctx.send("Sams turned off")
        else:
            await rust_socket.turn_on_smart_switch(sam)
            await ctx.send("Sams turned on")
    await rust_socket.disconnect()


@bot.command()
async def curtime(ctx):
    await rust_socket.connect()
    await ctx.send(f"Current in-game time: {(await rust_socket.get_time()).time}")
    await rust_socket.disconnect()

@bot.command()
async def team(ctx):
    await rust_socket.connect()
    team_info = await rust_socket.get_team_info()
    for member in team_info.members:
        embed = embed = discord.Embed(title=member.name, url="",
                              description="",
                              color=0xce412b)
        embed.add_field(name="x_pos", value=f"{member.x}",
                        inline=False)
        embed.add_field(name="y_pos", value=f"{member.y}",
                        inline=False)
        embed.add_field(name="Is Online", value=f"{member.is_online}",
                        inline=False)
        embed.add_field(name="Is Alive", value=f"{member.is_alive}",
                        inline=False)
        await ctx.send(embed=embed)

        # steam_id: int
        # name: str
        # x: float
        # y: float
        # is_online: bool
        # spawn_time: int
        # is_alive: bool
        # death_time: int

    await rust_socket.disconnect()

@bot.command()
async def server(ctx):
    await rust_socket.connect()

    server_info = await rust_socket.get_info()

    embed = discord.Embed(title="Server Information", url="",
                          description="",
                          color=0xce412b)
    embed.add_field(name="Name", value=server_info.name,
                    inline=False)
    embed.add_field(name="Population", value=f"{server_info.players}/{server_info.max_players}",
                    inline=False)
    embed.add_field(name="Current Queue", value=f"{server_info.queued_players} players",
                    inline=False)

    await ctx.send(embed=embed)
    await rust_socket.disconnect()

@bot.command()
async def sendmessage(ctx):
    await rust_socket.connect()

    await rust_socket.send_team_message("Testing 123")
    await rust_socket.disconnect()

@bot.command()
async def chanid(ctx):
    await rust_socket.connect()

    channel = discord.utils.get(ctx.guild.channels, name="team-chat")
    await channel.send("Team chat will display here")
    await channel.send(ctx.guild.id)
    await rust_socket.disconnect()


@bot.command()
async def loadchat(ctx):
    await rust_socket.connect()
    channel = discord.utils.get(ctx.guild.channels, name="team-chat")
    discordMessages = await channel.history(limit=2).flatten()

    chatList = await rust_socket.get_team_chat()

    # If the last message in the list of team chat (most recent 20 messages) is not equal to the most recent message in discord channel then send it
    nextMessage = f"{chatList[-1].time}{chatList[-1].name}: {chatList[-1].message}"
    if nextMessage != discordMessages[0].content and nextMessage != discordMessages[1].content:
        await channel.send(nextMessage)
    await rust_socket.disconnect()

# Team Chat - maybe an array for current chat in the channel to track messages from discord user - look into time
# - Load the array from rust+ on startup.
#    - Search all recent discord messages and if the content matches elements in array dont post them
#    - If array is empty just break
# - Once loaded, run start a task loop to constantly check every second or so and run the same checks
# - If someone types in chat it takes their discord name and appends to front of message content
#   - Sends message to team chat
#
@bot.command()
async def load(ctx):
    await rust_socket.connect()
    channel = discord.utils.get(ctx.guild.channels, name="team-chat")
    messages = await channel.history(limit=5).flatten()

    chatList = await rust_socket.get_team_chat()

    for msg in messages:
        username = msg.author.name
        for teamMessage in chatList:
            if not msg.content == teamMessage.message or not username + ": " + msg.content == teamMessage.message:
                print(f"Should be sent to discord\n{teamMessage.message}")
                await channel.send(teamMessage.name + ": " + teamMessage.message)
            else:
                print(f"Should not be sent to discord\n{teamMessage.message}")


    print(messages)
    print(chatList)
    print(f"MESSAGES TYPE {type(messages)}\nCHATLIST TYPE: {type(chatList)}\nCHATLISTEL TYPE: {type(chatList[0])}")
    await rust_socket.disconnect()


@bot.command()
async def map(ctx):
    await rust_socket.connect()
    game_map = await rust_socket.get_map(add_icons=True, add_events=True, add_vending_machines=True)

    game_map.save("map.png", "PNG")

    file = discord.File("map.png")
    embed = discord.Embed(title="Current Map", url="",
                          description="",
                          color=0xce412b)
    embed.set_image(url="attachment://map.png")
    await ctx.send(file=file, embed=embed)
    await rust_socket.disconnect()

# @bot.command()
# async def events(ctx):
#     await rust_socket.connect()
#
#     eventList = await rust_socket.get_markers()
#
#     embed = discord.Embed(title="Events", url="",
#                           description="",
#                           color=0xce412b)
#     for event in eventList:
#         if event.type == 5:
#             cargoStatus = "out"
#         else:
#             cargoStatus = "not out"
#         embed.add_field(name="Cargo Status", value=cargoStatus,
#                         inline=False)
#
#     await ctx.send(embed=embed)
#     await rust_socket.disconnect()

# lists commands for rust help
@bot.command()
async def rust(ctx):
    embed = discord.Embed(title="Dragon Bot Rust Commands", url="",
                          description="This is a collection of useful Rust commands for Dragon Bot",
                          color=0xce412b)
    embed.set_thumbnail(url="https://www.logolynx.com/images/logolynx/00/00ffc7e57ffb143ce0dd3343aa5a59a7.png")

    # Actual commands belong below
    # embed.add_field(name="!rads", value="Lists the rads for each monument",
    #                 inline=False)
    # embed.add_field(name="!upgrade", value="Lists upgrade cost for each square, triangle, etc",
    #                 inline=False)
    # embed.add_field(name="!raid [arg]", value="Lists raid cost for walls or deployables",
    #                 inline=False)
    embed.add_field(name="!curtime", value="Returns current in-game time",
                    inline=False)
    # embed.add_field(name="!entities", value="Lists paired entities and their ID's",
    #                 inline=False)
    embed.add_field(name="!sams", value="Toggles sams on or off and returns new value",
                    inline=False)
    embed.add_field(name="!map", value="Returns map information",
                    inline=False)
    #embed.add_field(name="!send [msg]", value="Sends a message to teamchat if you have a bound rust+ account",
    #                inline=False)
    # embed.add_field(name="!events", value="Returns status of oil/cargo etc",
    #                 inline=False)
    # embed.add_field(name="!promote [name]", value="Promotes the player to teamleader",
    #                 inline=False)
    # embed.add_field(name="!bind [STEAM64ID] [PLAYERTOKEN]", value="Binds your Rust+ to your discord user",
    #                 inline=False)
    embed.add_field(name="!team", value="Displays information about all members in team",
                    inline=False)
    embed.add_field(name="!server", value="Displays server information",
                    inline=False)
    await ctx.send(embed=embed)
    # await ctx.send("Rust Commands:\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n"
    #                "\n")



# Run bot
bot.run(creds.api_key)
