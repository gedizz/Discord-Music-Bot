class SongQueue:

    def __init__(self):
        self.queue_list = []

    async def add(self, song_name, append):
        self.queue_list.insert(0, song_name) if append else self.queue_list.append(song_name)

    async def pop(self):
        print(self.queue_list)
        try:
            song = self.queue_list[0]
            del(self.queue_list[0])
            return song
        except:
            return None

    async def remove_from_queue(self, index):
        try:
            song = self.queue_list[index - 1].replace(".mp3", "")
            del(self.queue_list[index - 1])
            return song
        except:
            return None

    async def display_queue(self, ctx):
        song_num = 1
        if self.queue_list:
            for song in self.queue_list:
                song = song.replace(".mp3", "")
                await ctx.send(f"{song_num}) - {song}")
                song_num += 1
        else:
            await ctx.send("Queue is empty")

    async def is_empty(self):
        return False if self.queue_list else True

    async def clear_queue(self):
        self.queue_list = []


