from SongQueue import SongQueue
from discord.ext import commands, tasks
import discord
import creds
import yt_dlp

class Player:

    def __init__(self, guild):
        self.queue = SongQueue()
        self.now_playing = ""
        self.volume = 0.02
        self.guild = guild
        self.idle_time = 0
        self.no_users_listening = 0
        self.max_vol = 1.0
        self.min_vol = 0.0
        self.is_streaming = False
        self.explicit = False
        # self.volume = self.voice.source.volume

    def play_audio(self, song_to_play, voice_client):
        audio_source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(source=f"{song_to_play}",
                                   executable=creds.ffmpeg_location))

        # play and set volume to default
        voice_client.play(audio_source, after=None)
        voice_client.source.volume = self.volume

    async def stream_audio(self, voice_client, url, YDL_OPTS, ctx):
        if not voice_client.is_playing():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)

            # a Google video api link obtained from yt_dl that is played with local VLC player through voice_client
            extracted_url = info['formats'][0]['url']
            stream_title = info['title']

            # Prevents not playing from certain audio sources due to:
            # https://support.discord.com/hc/en-us/articles/360035010351--Known-Issue-Music-Bots-Not-Playing-Music-From-Certain-Sources

            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                              'options': '-vn'}
            # Sets our standard volume transformer
            audio_source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(extracted_url, **ffmpeg_options))
            # class discord.FFmpegPCMAudio(source, *, executable='ffmpeg', pipe=False, stderr=None, before_options=None, options=None)

            # finally plays the audio through our voice and sets volume
            voice_client.play(audio_source, after=None)
            voice_client.source.volume = self.volume
            await ctx.send(f"Now streaming {stream_title}")
            self.now_playing = stream_title
        else:
            await ctx.send("Already playing song")

    def adjust_volume(self, new_volume, voice_client):
        voice_client.source.volume = new_volume
        self.volume = new_volume
