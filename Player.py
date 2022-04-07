from SongQueue import SongQueue
from discord.ext import commands, tasks
import discord
import creds


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
        # self.volume = self.voice.source.volume

    def play_audio(self, song_to_play, voice_client):
        audio_source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(source=f"{song_to_play}",
                                   executable=creds.ffmpeg_location))

        # play and set volume to default
        voice_client.play(audio_source, after=None)
        voice_client.source.volume = self.volume
