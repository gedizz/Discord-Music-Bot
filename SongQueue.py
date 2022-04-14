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
        formatted_list = []
        # Instead of awaiting every time we send a message and causing it to take longer, just format the list first
        if self.queue_list:
            for song in self.queue_list:
                song = song.replace(".mp3", "")
                formatted_song = f"{song_num}) - {song}"
                formatted_list.append(formatted_song)
                song_num += 1
            # Then send one message to the chat with a formatted list.
            await ctx.send("\n\n" .join(formatted_list))

        else:
            await ctx.send("Queue is empty")

    async def is_empty(self):
        return False if self.queue_list else True

    async def clear_queue(self):
        self.queue_list = []


