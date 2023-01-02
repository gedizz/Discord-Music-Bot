from rustplus import RustSocket, FCMListener, CommandOptions, Command
import json
import asyncio
import math

STANDARDX = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
            "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z","aa"]
STANDARDY = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
##UTILITY
async def determine_crate_location(crate):
    map_data = await rust_socket.get_raw_map_data()
    for mon in map_data.monuments:
        distance = math.sqrt(abs(crate.x - mon.x) ** 2 + abs(crate.y - mon.y) ** 2)
        if distance < 150:
            return mon.token


async def determine_coordinate(x, y):

    x_math = x / 146
    y_math = y / 148
    x_index = math.floor(x_math)
    y_index = math.ceil(y_math)

    grid = f"{STANDARDX[x_index]}{STANDARDY[-y_index]}".upper()
    print(f"Passed: ({x}, {y})\n"
          f"After Math: ({x_math}, {y_math})\n"
          f"After Round: ({x_index}, {y_index})\n"
          f"Grid: {grid}")
    return grid

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
        await rust_socket.send_team_message(f"--Turret Switch {i + 1}: {turret.value}")
    for i in range(0, len(ENTITIES["sams"])):
        sam = await rust_socket.get_entity_info(ENTITIES["sams"][i])
        await rust_socket.send_team_message(f"--SAM Switch {i + 1}: {sam.value}")

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
async def dragon(command: Command):
    team_info = await rust_socket.get_team_info()
    for member in team_info.members:
        if member.name == "X7 Dragon":
            member_grid = await determine_coordinate(member.x, member.y)

            await rust_socket.send_team_message(f"Dragon is in {member_grid}")



@rust_socket.command()
async def events(command: Command):
    event_list = await rust_socket.get_current_events()
    cargo_active = "Not Active"
    heli_active = "Not Active"
    large_crate = "No crate"
    small_crate = "No crate"
    regular_crate = "No crate dropped"
    explosion_status = "Not active"

    for event in event_list:

        if event.type == 2: # Explosion is active
            location = await determine_crate_location(event)
            if location:
                explosion_status = location
            else:
                explosion_status = await determine_coordinate(event.x, event.y)

        elif event.type == 5: # The event is cargo
            num_crates = 0
            # determine if and how many crates are on
            for cargo_crate in event_list:
                if cargo_crate.type == 6:
                    distance = math.sqrt(abs(cargo_crate.x - event.x) ** 2 + abs(cargo_crate.y - event.y) ** 2)
                    if distance < 150:
                        num_crates += 1
            # Update the message to send now that the number of crates is determined
            cargo_active = f"Active: {num_crates} crate(s)"

        elif event.type == 8: # The event is heli
            heli_active = "Active"

        elif event.type == 6: # It's a crate not aforementioned
            location = await determine_crate_location(event)
            if location == "large_oil_rig":
                large_crate = "Crate available"
            elif location == "oil_rig_small":
                small_crate = "Crate available"
            elif location != "oil_rig_small" and location != "large_oil_rig":
                regular_crate = location

        print(event.name)
        print(event.id)
        print(event.type)

    await rust_socket.send_team_message(f"Cargo: {cargo_active}")
    await rust_socket.send_team_message(f"Heli: {heli_active}")
    await rust_socket.send_team_message(f"Large Oil: {large_crate}")
    await rust_socket.send_team_message(f"Small Oil: {small_crate}")
    await rust_socket.send_team_message(f"Chinook Crate: {regular_crate}")
    # End of grand loop



@rust_socket.command()
async def help(command: Command):
    await rust_socket.send_team_message(".!pop - Displays current pop info")
    await rust_socket.send_team_message(".!curtime - Displays current pop info")
    await rust_socket.send_team_message(".!sams [on/off] - Toggles sams or turns them all on/off")
    await rust_socket.send_team_message(".!turrets [on/off] - Toggles turrets or turns them all on/off")
    await rust_socket.send_team_message(".!status - Displays current switch statuses ")
    await rust_socket.send_team_message(".!events - Displays status of oil, cargo, heli, etc. ")
    await rust_socket.send_team_message(".!dragon - Tells you where dragon is")



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