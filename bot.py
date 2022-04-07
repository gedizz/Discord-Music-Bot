import discord
from discord.ext import commands, tasks
import creds
from Player import Player
import os
import urllib.request
import requests
import yt_dlp
import re
import threading as th

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
    #explicit = guild_dict[ctx.guild]["explicit"]
    #if explicit:  # adds explicit to the end of explicit searching is on
        #keywords.append("explicit")
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


async def queue_check(guild):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=guild)
    player = guild_dict[guild]
    queue = player.queue
    print(f"queue checked for: {guild}")
    if voice_client:
        if not await queue.is_empty() and not voice_client.is_playing() and not voice_client.is_paused():
            print(await queue.q_to_list())
            song_to_play = queue.remove_from_queue(0)
            player.play_audio(song_to_play, voice_client, guild)

            #global idle_time
            #idle_time = 0  # set global idle time to 1 so bot doesn't disconnect from leave_after_5 loop
            player.now_playing = song_to_play
        elif await queue.is_empty():
            print("From 'check_queue': Queue empty")
        else:
            print("From 'check_queue': Song playing")


####################
###  Task Loops  ###
####################
@tasks.loop(seconds=3.0)
async def check_queue():
    for guild in bot.guilds: # Need to change this to a thread for each guild. Works for now though
        thread = th.Thread(target=queue_check, args=guild)
        thread.start()


##############
##  Events  ##
##############
@bot.event
async def on_ready():
    print("Bot is ready")
    for guild in bot.guilds:
        guild_dict[guild] = Player(guild)


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
async def join(ctx):
    channel = ctx.author.voice.channel
    await channel.connect()


@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()


@bot.command()
async def q(ctx):
    queue = guild_dict[ctx.guild].queue
    await queue.display_queue(ctx)


@bot.command()
async def remove(ctx, idx: int):
    queue = guild_dict[ctx.guild].queue
    song = await queue.remove_from_queue(idx)
    await ctx.send(f"{song} removed from the queue") if song else await ctx.send("There is no song in the queue for that number")

# Run bot
bot.run(creds.api_key)
