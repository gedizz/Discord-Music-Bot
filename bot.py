import os
import re
import threading as th
import urllib.request
import discord
import yt_dlp
from discord.ext import commands, tasks
from discord.utils import get
import creds
from Player import Player
from rustplus import RustSocket, FCMListener, CommandOptions, Command
from PIL import Image
import logging
import math
import requests

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
# init player
bot = commands.Bot(command_prefix='!', help_command=None)
guild_dict = {}

# CONSTANTS

YOUTUBE_URL_START = "https://youtube.com/results?search_query="
YDL_OPTS = {'format': 'bestaudio/best',
            'extractaudio': True,
            'ratelimit': 15000000,
            'ffmpeg_location': creds.ffmpeg_location,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            }

ENTITIES = {
    "sams": [23092110],
    "turrets": [14764611, 14995747],
}


###########################
###  Utility Functions  ###
###########################

async def grid():
    info = await rust_socket.get_info()
    size = info.size
    map = await rust_socket.get_map(True, True, False)
    url = f'https://files.rustmaps.com/grids/{size}.png'
    grid = Image.open(requests.get(url, stream=True).raw)
    Grid_Fixed = grid.resize((2000, 2000), Image.ANTIALIAS)
    map.paste(Grid_Fixed, (0, 0), Grid_Fixed)
    return map


async def download_using_url(url: str, append: bool, ctx):
    queue = guild_dict[ctx.guild].queue
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        # extract video title from video referenced by url
        info_dict = ydl.extract_info(url, download=False)  # print this out sometime. It has a lot of interesting stuff
        raw_file_name = ydl.prepare_filename(info_dict)  # YoutubeDL method that returns videos default file name
        raw_file_name = raw_file_name.replace(".webm", ".mp3")  # replace the webm with mp3
        video_id = info_dict["id"]  # video ID that is appended to end of file name by default

        # 'id' key in info_dict is added to the end of the file as such:
        # "filename [id].mp3"
        file_without_id = raw_file_name.replace(f" [{video_id}]", "")  # removes video id at the end of each file name

        # If song exists already then it's good to go, otherwise download and rename the song
        final_name = file_without_id if os.path.exists(file_without_id) \
            else rename_and_download(raw_file_name, file_without_id, url, ydl)

        # Check if appending to front or back of queue, then perform appropriate action.
        # print("URL AFTER DL: %s\n\n\n", url)
        await queue.add(final_name, append)
        # await queue.print_list()
        return final_name  # return the file name to play() or to download_using_keywords()


async def download_using_keywords(keywords, append: bool, ctx):
    request = YOUTUBE_URL_START
    player = guild_dict[ctx.guild]
    if player.explicit:  # adds explicit to the end of explicit searching is on
        keywords.append("explicit")
    for key in keywords:
        request += key
        request += "+"
    html = urllib.request.urlopen(request)
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    # return to play()
    return await download_using_url("https://www.youtube.com/watch?v=" + video_ids[0], append, ctx)


# The file didn't exist so we download it and return the renamed file name to append to queue
def rename_and_download(raw_file_name, file_without_id, url, ydl):
    ydl.download(url)
    for file in os.listdir("./"):
        if file.startswith(raw_file_name):
            os.rename(file, file_without_id)
    return file_without_id


async def listening_check(guild):
    player = guild_dict[guild]
    queue = player.queue
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    if voice_client:
        # gets channel bot is connected to and all members in that channel
        channel = voice_client.channel
        member_ids = channel.voice_states.keys()
        users_connected = len(member_ids)

        # If the bot is alone, add to no_users_connected_timer
        if users_connected <= 1:
            player.no_users_listening += 1

            if player.no_users_listening >= 100:
                await voice_client.disconnect()
                queue.clear_queue()
                print("bot disconnected: no users in channel for 5 minutes")
                no_users_connected_timer = 0

        # when not playing anything, add a minute and check if its at 5 minutes
        elif not voice_client.is_playing() and not voice_client.is_paused():
            player.idle_time += 1
            if player.idle_time >= 100:
                await voice_client.disconnect()
                queue.clear_queue()
                print(f"bot disconnected: idle for 5 minutes")
                idle_time = 0

        # Music is playing normally
        else:
            pass


async def queue_check(guild):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    player = guild_dict[guild]
    queue = player.queue
    print(f"queue checked for: {guild}")
    if voice_client:
        if not await queue.is_empty() and not voice_client.is_playing() and not voice_client.is_paused():
            song_to_play = await queue.pop()
            player.play_audio(song_to_play, voice_client)
            # global idle_time
            # idle_time = 0  # set global idle time to 1 so bot doesn't disconnect from leave_after_5 loop
            player.now_playing = song_to_play


####################
###  Task Loops  ###
####################
@tasks.loop(seconds=3.0)
async def guild_tasks():
    for guild in bot.guilds:
        que_ck = th.Thread(target=await queue_check(guild))
        que_ck.start()
        listen_check = th.Thread(target=await listening_check(guild))
        listen_check.start()


##############
##  Events  ##
##############
@bot.event
async def on_ready():
    num_guilds = len(bot.guilds)
    for guild in bot.guilds:
        guild_dict[guild] = Player(guild)
        print(f"Bot is ready on: {guild}")
    # await asyncio.sleep(2)
    guild_tasks.start()
    await rust_socket.connect()
    print(f"Rust+ Bot Online")
    await bot.change_presence(activity=discord.Game(name="music | !help"))

    # pool = ThreadPool()
    # pool.map(await check_queue.start(guild))


# handles all messages from users. Will force all commands to be lowercase
@bot.event
async def on_message(message):
    # make list to find first word in message.content and make ONLY that lowercase
    content_list = message.content.split()
    for word in content_list:
        if word == content_list[0]:
            message.content = message.content.replace(word, word.lower())

    await bot.process_commands(message)


################
##  Commands  ##
################
@bot.command()
async def play(ctx, *args: str):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if ctx.author.voice is None:
        await ctx.send("You must be connected to a voice channel to run this command")
    else:
        if not voice_client:
            await join(ctx)

        keys = list(args)
        song_name = ""
        # print("URL BEFORE DL: %s\n\n\n", keys[0])

        # download if given a url
        if keys[0].startswith("http://www.youtube") or keys[0].startswith("https://www.youtube"):
            song_name = await download_using_url(keys[0], False, ctx)


        else:  # use keys as search terms when building url
            song_name = await download_using_keywords(keys, False, ctx)

        song_name = song_name.replace(".mp3", "")
        await ctx.send(f"{song_name} was added to the queue")


@bot.command()
async def append(ctx, *args: str):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if ctx.author.voice is None:
        await ctx.send("You must be connected to a voice channel to run this command")
    else:
        if not voice_client:
            await join(ctx)

        keys = list(args)
        song_name = ""

        # download if given a url
        if keys[0].startswith("http://www.youtube") or keys[0].startswith("https://www.youtube"):
            song_name = await download_using_url(keys[0], True, ctx)

        else:  # use keys as search terms when building url
            song_name = await download_using_keywords(keys, True, ctx)

        song_name = song_name.replace(".mp3", "")
        await ctx.send(f"{song_name} was added to the queue")


# Will stream audio given a youtube link - (brief="keyword to set help desc?")
@bot.command()
async def stream(ctx, url: str):
    player = guild_dict[ctx.guild]
    try:
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if ctx.author.voice is None:
            await ctx.send("You must be connected to a voice channel to run this command")
        else:
            if not voice_client:
                await join(ctx)
        await player.stream_audio(voice_client, url, YDL_OPTS, ctx)
    except:
        await ctx.send("That song cannot be streamed, maybe try again")


@bot.command()
async def skip(ctx):
    player = guild_dict[ctx.guild]
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Song skipped")
    else:
        await ctx.send("No audio playing")


# Toggles explicit searching through youtube keywords
@bot.command(aliases=['expl', 'explicit', 'exp'])
async def toggle_explicit(ctx):
    player = guild_dict[ctx.guild]
    if player.explicit:
        player.explicit = False
        await ctx.send("Explicit searching turned off")
    else:
        player.explicit = True
        await ctx.send("Explicit searching turned on")


@bot.command()
async def join(ctx):
    player = guild_dict[ctx.guild]
    player.no_users_listening = 0
    player.idle_time = 0
    channel = ctx.author.voice.channel
    await channel.connect()


@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()


@bot.command()
async def np(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue = guild_dict[ctx.guild].queue.queue_list
    now_playing = guild_dict[ctx.guild].now_playing.replace(".mp3", "")
    if voice_client.is_playing() and len(queue) >= 2:
        up_next = queue[0].replace(".mp3", "")
        in_hole = queue[1].replace(".mp3", "")
        await ctx.send(f"Now playing: {now_playing}\n\n"
                       f"Up next: {up_next}\n\n"
                       f"In the hole: {in_hole}")
    elif voice_client.is_playing() and len(queue) >= 1:
        up_next = queue[0].replace(".mp3", "")
        await ctx.send(f"Now playing: {now_playing}\n\n"
                       f"Up next: {up_next}")
    elif voice_client.is_playing():
        await ctx.send(f"Now playing: {now_playing}")
    else:
        await ctx.send("Nothing is currently playing")


@bot.command()
async def vol(ctx, *args: str):
    player = guild_dict[ctx.guild]
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    # no music playing or queued
    if not voice_client.is_playing() and not voice_client.is_paused():
        await ctx.send("Can't adjust volume when no song is playing")

    else:
        # They are just checking volume and passed no arguments
        if not args:
            await ctx.send(f"Current volume is {int(round(player.volume, 2) * 100)}")

        # They passed an argument so it's checked
        else:
            # stores the first arg passed
            volume = args[0]

            # if the string can parse to digit
            if volume.isdigit() and int(volume) in range(101):
                # if its a valid digit
                player.adjust_volume(float(int(volume) / 100), voice_client)
                player.volume = float(int(volume)) / 100
                await ctx.send(f"Volume set to {int(volume)}")


            # user wants to increase volume
            elif volume == "up":
                if player.volume <= 0.98:
                    volume = round(player.volume + 0.020, 2)
                    player.adjust_volume(volume, voice_client)
                    player.volume = volume
                    await ctx.send(f"Volume set to {int(volume * 100)}")
                else:
                    await ctx.send("What are you crazy? That's too loud")

            # User wants to decrease volume
            elif volume == "down":
                if player.volume >= 0.02:
                    volume = round(player.volume - 0.020, 2)
                    player.adjust_volume(volume, voice_client)
                    player.volume = volume
                    await ctx.send(f"Volume set to {int(volume * 100)}")
                else:
                    await ctx.send("Impossibly quiet...")

            # any input besides a number, up, or down
            else:
                await ctx.send("Volume must be up, down, or a number between 1-100")


# Stops the bot if it is currently playing and should likely clear queue
@bot.command()
async def stop(ctx):
    queue = guild_dict[ctx.guild].queue
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Song stopped, queue cleared")
        await queue.clear_queue()
    else:
        await ctx.send("No audio playing")


# pauses music
@bot.command()
async def pause(ctx):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Audio paused")
    else:
        await ctx.send("There is nothing playing. Try to !resume or !play a song")


# resumes music if paused
@bot.command()
async def resume(ctx):
    queue = guild_dict[ctx.guild].queue
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    # If nothing was playing then report to discord
    if not voice_client.is_playing() and await queue.is_empty() and not voice_client.is_paused():
        await ctx.send("There is no music to resume")
    # If audio was paused then just go ahead and resume it
    elif not voice_client.is_playing() and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Audio resumed")
    else:
        await ctx.send("Audio is already playing")


@bot.command()
async def q(ctx):
    queue = guild_dict[ctx.guild].queue
    await queue.display_queue(ctx)


@bot.command()
async def remove(ctx, idx: int):
    queue = guild_dict[ctx.guild].queue
    song = await queue.remove_from_queue(idx)
    await ctx.send(f"{song} removed from the queue") if song else await ctx.send(
        "There is no song in the queue for that number")

# clears all files in directory
@bot.command(aliases=["clr", "cls"])
async def clear(ctx):
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.remove(file)

@bot.command(aliases=["h"])
async def help(ctx):
    await ctx.send("Command provided by this bot are specified below:\n\n"

                   "!rust - Command list for rust help\n"
                   "!join - tells the bot to join your current voice channel\n"
                   "!leave - tells the bot to leave your current voice channel\n"
                   "!play [argument] - adds a song to the queue to play\n"
                   "    - [argument] can be...\n"
                   "        - a url to a youtube video\n"
                   "        - the keywords you want to use to search youtube\n"
                   "!vol [1-100] [up] [down] - Sets the volume of the bot\n"
                   "!q - Displays the current queue\n"
                   "!pause - pauses the audio\n"
                   "!resume - resumes the audio\n"
                   "!stop - stops audio and clears queue\n"
                   "!skip - skips the song currently playing\n"
                   "!stream - stream from youtube LIVE URL - not always functional\n"
                   "!append - adds a song to the front of the list\n"
                   "!np - Lists song currently playing\n"
                   "!explicit - toggles explicit searching with youtube keywords\n"
                   "!clear - Clears all downloaded songs\n"
                   "!remove [num in queue] - Removes a song from the current queue")


# RUST PLUS
# us-2x.stomptown.gg:28015

# with open("rustplus.py.config.json", "r") as input_file:
#     fcm_details = json.load(input_file)
#
#
# class FCM(FCMListener):
#
#     def on_notification(self, obj, notification, data_message):
#         print(notification)
#
#
# FCM(fcm_details).start()

STANDARDX = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
            "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z","aa"]
STANDARDY = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]

STEAMID = 76561198040853461  # my steam id -- never changes
PLAYERTOKEN = -432760157  # my player token. Might change

# options = CommandOptions(prefix="!") # Use whatever prefix you want here
rust_socket = RustSocket("154.16.128.35", "28017", STEAMID, PLAYERTOKEN, raise_ratelimit_exception=False)

####################
### RUST UTILITY ###
####################
# train_tunnel_display_name
# train_tunnel_display_name
# train_tunnel_display_name
# DungeonBase
# DungeonBase
# DungeonBase
# DungeonBase
# DungeonBase
# DungeonBase
# arctic_base_a
# large_fishing_village_display_name
# fishing_village_display_name
# fishing_village_display_name
# harbor_display_name
# train_tunnel_display_name
# harbor_2_display_name
# train_tunnel_display_name
# airfield_display_name
# train_tunnel_display_name
# excavator
# train_tunnel_display_name
# military_tunnels_display_name
# train_tunnel_display_name
# power_plant_display_name
# train_tunnel_display_name
# train_yard_display_name
# train_tunnel_display_name
# water_treatment_plant_display_name
# train_tunnel_display_name
# lighthouse_display_name
# lighthouse_display_name
# outpost
# train_tunnel_display_name
# sewer_display_name
# AbandonedMilitaryBase
# large_oil_rig
# oil_rig_small
# gas_station
# supermarket
# supermarket
# supermarket
# mining_outpost_display_name
# mining_outpost_display_name
# satellite_dish_display_name
# dome_monument_name
# stables_a
# stables_b
# underwater_lab
# DungeonBase
# underwater_lab
# DungeonBase
# underwater_lab
# DungeonBase
# launchsite
# train_tunnel_display_name
async def determine_crate_location(crate):
    map_data = await rust_socket.get_raw_map_data()
    for mon in map_data.monuments:
        distance = math.sqrt(abs(crate.x - mon.x) ** 2 + abs(crate.y - mon.y) ** 2)
        if distance < 150:
            return mon.token


async def determine_coordinate(x, y):

    x_math = x / 146
    y_math = y / 146
    x_index = math.floor(x_math)
    y_index = math.ceil(y_math)

    grid = f"{STANDARDX[x_index]}{STANDARDY[-y_index]}".upper()
    print(f"Passed: ({x}, {y})\n"
          f"After Math: ({x_math}, {y_math})\n"
          f"After Round: ({x_index}, {y_index})\n"
          f"Grid: {grid}")
    return grid

@bot.command()
async def sams(ctx, *args: str):
    sams_list = ENTITIES["sams"]

    if args:
        if args[0] == "off":
            for sam in sams_list:
                await rust_socket.turn_off_smart_switch(sam)
            await ctx.send("All sam switches turned off")

        elif args[0] == "on":
            for sam in sams_list:
                await rust_socket.turn_on_smart_switch(sam)
            await ctx.send("All sam switches turned on")

        else:
            await ctx.send("Invalid argument. Please use !sams [on/off]")
    else:

        for sam in sams_list:
            sam_info = await rust_socket.get_entity_info(sam)
            if sam_info.value:
                await rust_socket.turn_off_smart_switch(sam)
            else:
                await rust_socket.turn_on_smart_switch(sam)
        await ctx.send("All sam switches toggled")


@bot.command()
async def turrets(ctx, *args: str):
    turret_list = ENTITIES["turrets"]

    if args:
        if args[0] == "off":
            for turret in turret_list:
                await rust_socket.turn_off_smart_switch(turret)
            await ctx.send("All turret switches turned off")

        elif args[0] == "on":
            for turret in turret_list:
                await rust_socket.turn_on_smart_switch(turret)
            await ctx.send("All turret switches turned on")

        else:
            await ctx.send("Invalid argument. Please use !turrets [on/off]")
    else:

        for turret in turret_list:
            turret_info = await rust_socket.get_entity_info(turret)
            if turret_info.value:
                await rust_socket.turn_off_smart_switch(turret)
            else:
                await rust_socket.turn_on_smart_switch(turret)
        await ctx.send("All turret switches toggled")


@bot.command()
async def curtime(ctx):
    await ctx.send(f"Current in-game time: {(await rust_socket.get_time()).time}")


@bot.command()
async def team(ctx):
    team_info = await rust_socket.get_team_info()
    for member in team_info.members:
        member_grid = await determine_coordinate(member.x, member.y)
        embed = embed = discord.Embed(title=member.name, url="",
                                      description="",
                                      color=0xce412b)
        embed.add_field(name="Grid:", value=f"{member_grid}",
                        inline=True)
        embed.add_field(name="Is Online", value=f"{member.is_online}",
                        inline=True)
        embed.add_field(name="Is Alive", value=f"{member.is_alive}",
                        inline=True)
        await ctx.send(embed=embed)

        # steam_id: int
        # name: str
        # x: float
        # y: float
        # is_online: bool
        # spawn_time: int
        # is_alive: bool
        # death_time: int


@bot.command()
async def server(ctx):
    map = await rust_socket.get_raw_map_data()

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
    embed.add_field(name="Map Size", value=f"{map.width}x{map.height}",
                    inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def chanid(ctx):
    channel = discord.utils.get(ctx.guild.channels, name="team-chat")
    await channel.send("Team chat will display here")
    await channel.send(ctx.guild.id)

@bot.command()
async def dragon(ctx):
    team_info = await rust_socket.get_team_info()
    for member in team_info.members:
        if member.name == "X7 Dragon":
            member_grid = await determine_coordinate(member.x, member.y)

            await ctx.send(member_grid)


@bot.command()
async def loadchat(guild):
    channel = discord.utils.get(guild.channels, name="team-chat")
    chatList = await rust_socket.get_team_chat()

    messages = await channel.history(limit=2).flatten()
    # await ctx.send(messages[1].content)
    # If the last message in the list of team chat (most recent 20 messages) is not equal to the most recent message in discord channel then send it
    nextMessage = f"{chatList[-1].name}: {chatList[-1].message}"
    if (nextMessage != messages[0].content):
        await channel.send(nextMessage)


@bot.command()
async def map(ctx):
    game_map = await rust_socket.get_map(add_icons=True, add_events=True, add_vending_machines=True)
    game_map_with_grid = await grid()
    game_map_with_grid.save("map.png", "PNG")

    file = discord.File("map.png")
    embed = discord.Embed(title="Current Map", url="",
                          description="",
                          color=0xce412b)
    embed.set_image(url="attachment://map.png")
    await ctx.send(file=file, embed=embed)

    # Player = 1
    # Explosion = 2
    # VendingMachine = 3
    # CH47 = 4
    # CargoShip = 5
    # Crate = 6
    # GenericRadius = 7
    # PatrolHelicopter = 8

@bot.command()
async def events(ctx):
    event_list = await rust_socket.get_current_events()
    cargo_active = "Not Active"
    heli_active = "Not Active"
    large_crate = "No crate"
    small_crate = "No crate"
    regular_crate = "No crate dropped"
    explosion_status = "Not active"

    for event in event_list:

        if event.type == 2: # Explosion is active
            location = await determine_crate_location(event)
            if location:
                explosion_status = location
            else:
                explosion_status = await determine_coordinate(event.x, event.y)

        elif event.type == 5: # The event is cargo
            num_crates = 0
            # determine if and how many crates are on
            for cargo_crate in event_list:
                if cargo_crate.type == 6:
                    distance = math.sqrt(abs(cargo_crate.x - event.x) ** 2 + abs(cargo_crate.y - event.y) ** 2)
                    if distance < 150:
                        num_crates += 1
            # Update the message to send now that the number of crates is determined
            cargo_active = f"Active: {num_crates} crate(s)"

        elif event.type == 8: # The event is heli
            heli_active = "Active"

        elif event.type == 6: # It's a crate not aforementioned
            location = await determine_crate_location(event)
            if location == "large_oil_rig":
                large_crate = "Crate available"
            elif location == "oil_rig_small":
                small_crate = "Crate available"
            elif location != "oil_rig_small" and location != "large_oil_rig":
                regular_crate = location

        print(event.name)
        print(event.id)
        print(event.type)

    # End of grand loop
    embed = discord.Embed(title=":map: Server Events", url="",
                          description="",
                          color=0xce412b)
    embed.add_field(name=":boom: Explosion", value=explosion_status,
                    inline=False)
    embed.add_field(name=":helicopter: Helicopter", value=heli_active,
                    inline=False)
    embed.add_field(name=":cruise_ship: Cargo", value=cargo_active,
                    inline=False)
    embed.add_field(name=":airplane: Chinook", value="Not active",
                    inline=False)
    embed.add_field(name=":package: Crate", value=regular_crate,
                    inline=False)
    embed.add_field(name=":oil: Small Oil", value=small_crate,
                    inline=False)
    embed.add_field(name=":oil: Large Oil", value=large_crate,
                    inline=False)



    await ctx.send(embed=embed)



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
    embed.add_field(name="!sams [on/off]", value="Toggles sams or when passed an argument turns all on/off",
                    inline=False)
    embed.add_field(name="!turrets [on/off]", value="Toggles turrets or when passed an argument turns all on/off",
                    inline=False)
    embed.add_field(name="!map", value="Returns map information",
                    inline=False)
    # embed.add_field(name="!send [msg]", value="Sends a message to teamchat if you have a bound rust+ account",
    #                inline=False)
    embed.add_field(name="!events", value="Returns status of oil/cargo etc",
                    inline=False)
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
# bot.run(creds.api_key, log_handler=handler)
bot.run(creds.api_key)
