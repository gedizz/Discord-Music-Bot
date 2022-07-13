# RUST PLUS
# us-2x.stomptown.gg:28015

from rustplus import RustSocket, FCMListener, CommandOptions, Command
import json

with open("rustplus.py.config.json", "r") as input_file:
    fcm_details = json.load(input_file)


class FCM(FCMListener):

    def on_notification(self, obj, notification, data_message):
        print(notification)


FCM(fcm_details).start()

STEAMID = 76561198040853461
PLAYERTOKEN = 30425580

options = CommandOptions(prefix="!") # Use whatever prefix you want here
rust_socket = RustSocket("154.16.128.35", "28017", STEAMID, PLAYERTOKEN)

rust_socket.connect()
