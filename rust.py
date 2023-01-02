from rustplus import RustSocket, FCMListener, CommandOptions, Command
import json
import asyncio




#CONSTANTS

STEAMID = 76561198040853461  # Current: Tag      Mine -- 76561198040853461
PLAYERTOKEN = 1167203602    # Current: Tag     Mine -- -432760157

ENTITIES = {
    "sams": [9135471],
    "turrets": [12708443, 12708606],
}

# options = CommandOptions(prefix="!") # Use whatever prefix you want here
# rust_socket = RustSocket("154.16.128.35", "28017", STEAMID, PLAYERTOKEN, raise_ratelimit_exception=False, command_options=options)
#
#
# async def main():
#     print("Rust+ Tracker Online")
#     await rust_socket.hang()

options = CommandOptions(prefix="!")
rust_socket = RustSocket("64.40.8.149", "28085", STEAMID, PLAYERTOKEN, raise_ratelimit_exception=False, command_options=options)

loop = asyncio.get_event_loop()

async def connect():
    await rust_socket.connect()
    print("Connected")

loop.create_task(connect())

@rust_socket.command()
async def hi(command: Command):
    if command.sender_name == "Orphan bonfire":
        await rust_socket.send_team_message(f"Hi, cheater!")
    else:
        await rust_socket.send_team_message(f"Hi, {command.sender_name}")

@rust_socket.command()
async def status(command: Command):
    await rust_socket.send_team_message(f"Switch Status:")

    for i in range(0, len(ENTITIES["turrets"])):
        turret = await rust_socket.get_entity_info(ENTITIES["turrets"][i])
        await rust_socket.send_team_message(f"--Turret Switch {i}: {turret.value}")
    for i in range(0, len(ENTITIES["sams"])):
        sam = await rust_socket.get_entity_info(ENTITIES["sams"][i])
        await rust_socket.send_team_message(f"--SAM Switch {i}: {sam.value}")

@rust_socket.command()
async def sams(command: Command):
    sams_list = ENTITIES["sams"]

    if command.args:
        if len(command.args) > 1:
            await rust_socket.send_team_message("Invalid argument. Please use !sams [on/off]")
        elif command.args[0] == "off":
            for sam in sams_list:
                await rust_socket.turn_off_smart_switch(sam)
            await rust_socket.send_team_message("All sam switches turned off")

        elif command.args[0] == "on":
            for sam in sams_list:
                await rust_socket.turn_on_smart_switch(sam)
            await rust_socket.send_team_message("All sam switches turned on")

        else:
            await rust_socket.send_team_message("Invalid argument. Please use !sams [on/off]")
    else:
        msg = "on"
        for sam in sams_list:
            sam_info = await rust_socket.get_entity_info(sam)
            if sam_info.value:
                msg = "off"
                await rust_socket.turn_off_smart_switch(sam)
            else:
                await rust_socket.turn_on_smart_switch(sam)
        await rust_socket.send_team_message(f"All sam turned {msg}")

@rust_socket.command()
async def turrets(command: Command):
    turrets_list = ENTITIES["turrets"]

    if command.args:
        if len(command.args) > 1:
            await rust_socket.send_team_message("Invalid argument. Please use !turrets [on/off]")
        elif command.args[0] == "off":
            for turret in turrets_list:
                await rust_socket.turn_off_smart_switch(turret)
            await rust_socket.send_team_message("All turret switches turned off")

        elif command.args[0] == "on":
            for turret in turrets_list:
                await rust_socket.turn_on_smart_switch(turret)
            await rust_socket.send_team_message("All turret switches turned on")

        else:
            await rust_socket.send_team_message("Invalid argument. Please use !turrets [on/off]")
    else:

        msg = "on"
        for turret in turrets_list:
            turret_info = await rust_socket.get_entity_info(turret)
            if turret_info.value:
                msg = "off"
                await rust_socket.turn_off_smart_switch(turret)
            else:
                await rust_socket.turn_on_smart_switch(turret)
        await rust_socket.send_team_message(f"All turret switches turned {msg}")


@rust_socket.command()
async def curtime(command: Command):
    await rust_socket.send_team_message(f"Current time: {(await rust_socket.get_time()).time}")


@rust_socket.command()
async def pop(command: Command):
    server_info = await rust_socket.get_info()
    await rust_socket.send_team_message(f"Pop: {server_info.players}/{server_info.max_players}")
    await rust_socket.send_team_message(f"Queue: {server_info.queued_players} players")


@rust_socket.command()
async def help(command: Command):
    await rust_socket.send_team_message(".!pop - Displays current pop info")
    await rust_socket.send_team_message(".!curtime - Displays current pop info")
    await rust_socket.send_team_message(".!sams [on/off] - Toggles sams or turns them all on/off")
    await rust_socket.send_team_message(".!turrets [on/off] - Toggles turrets or turns them all on/off")
    await rust_socket.send_team_message(".!status - Displays current switch statuses ")



# with open("rustplus.py.config.json", "r") as input_file:
#     fcm_details = json.load(input_file)


#
#
# class FCM(FCMListener):
#
#     def on_notification(self, obj, notification, data_message):
#         print(notification)


#FCM(fcm_details).start()

loop.run_forever()