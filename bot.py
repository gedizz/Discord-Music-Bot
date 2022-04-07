import os
import re
import threading as th
import time
import urllib.request
import discord
import yt_dlp
from discord.ext import commands, tasks
import creds
from Player import Player

# init player
bot = commands.Bot(command_prefix='!', help_command=None)
guild_dict = {}

#CONSTANTS

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


###########################
###  Utility Functions  ###
###########################
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
    queue = player.queue.queue_list
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
    time.sleep(2)
    guild_tasks.start()

        #pool = ThreadPool()
        #pool.map(await check_queue.start(guild))


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

        # download if given a url
        if keys[0].startswith("http://youtube") or keys[0].startswith("https://youtube"):
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
        if keys[0].startswith("http://youtube") or keys[0].startswith("https://youtube"):
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
    queue = guild_dict[ctx.guild]
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
    await ctx.send(f"{song} removed from the queue") if song else await ctx.send("There is no song in the queue for that number")


@bot.command(aliases=["h"])
async def help(ctx):
    await ctx.send("Command provided by this bot are specified below:\n\n"

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
                   "!explicit - toggles explicit searching with youtube keywords")


# clears all files in directory
@bot.command(aliases=["clr", "cls"])
async def clear(ctx):
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.remove(file)

# Run bot
bot.run(creds.api_key)
