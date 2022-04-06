import discord
from discord.ext import commands, tasks
import creds
from Player import Player
import os
import urllib.request
import requests
import yt_dlp
import re

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
    queue = guild_dict[ctx.guild]["queue"]
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
        await queue.append(final_name) if append else await queue.add(final_name)
        # await queue.print_list()
        return final_name  # return the file name to play() or to download_using_keywords()


async def download_using_keywords(keywords, append: bool, ctx):
    request = YOUTUBE_URL_START
    explicit = guild_dict[ctx.guild]["explicit"]
    if explicit:  # adds explicit to the end of explicit searching is on
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
