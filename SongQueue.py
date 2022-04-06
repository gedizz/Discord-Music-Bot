class SongQueue:

    def __init__(self):
        self.queue = []

    def add_to_queue(self, song_name):
        self.queue.append(song_name)

    def remove_from_queue(self, index):
        del(self.queue[index])
