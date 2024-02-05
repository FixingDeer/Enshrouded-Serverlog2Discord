import re
import time
import requests
from bs4 import BeautifulSoup
import json
import os
import configparser

# read config
config = configparser.ConfigParser()
config.read("config.ini")
log_dir = config["GAME"]["LogDirectory"]
webhook = config["DISCORD"]["Webhookurl"]
webhook_name = config["DISCORD"]["Webhookname"]

server_log = log_dir + "\\enshrouded_server.log"
file_size_log = ""

# check files if exist
if not os.path.exists(server_log):
    print("Please check your config, enshrouded_server.log not found")
    input("Press the <ENTER> key to continue...")
    exit()

# check log filesize (for detect new logfile)
file_size_log = os.stat(server_log).st_size

def read_log(logfile):
    global file_size_log
    logfile.seek(0, 2)
    while True:
        line = logfile.readline()
        if len(line) < 2:
            if file_size_log > os.stat(server_log).st_size:
                print(os.stat(server_log).st_size)
                exit()
            file_size_log = os.stat(server_log).st_size
            time.sleep(0.1)
            continue
        else:
            yield line


def get_steam_name_from_steamid(steamid):
    url = "https://steamcommunity.com/profiles/" + steamid
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        profile_name = soup.find('span', {'class': 'actual_persona_name'})
        if profile_name:
            return profile_name.text.strip()
        else:
            return "Name not found on profile"
    else:
        return "Failed to retrieve page"


# send discord webhook
def discord_webook(message):
    try:
        data = {}
        data["content"] = message
        data["username"] = webhook_name
        result = requests.post(webhook, data=json.dumps(data), headers={"Content-Type": "application/json"})
        result.raise_for_status()
    except Exception:
        print("an error occurred while sending the discord message")
        pass


def main():
    players_online = []
    player_info = []
    
    # open logfile
    try:
        logfile = open(server_log, "r", encoding="utf-8", errors="ignore")
    except OSError as err:
        print(f"an error occurred while opening the logfile ({err})")
        exit()

    # read logfile line
    for line in read_log(logfile):
        # First step of joining the server, get the Steam name from the SteamID logged and store in the players_online list
        # Also add the Steam name to the player_info list to be used by further steps
        if "authenticated by steam" in line:
            log_steamid = re.findall("Client '(\d+)' authenticated by steam", line)
            if not log_steamid:
                log_character = "Unknown Player"
            else:
                log_character = get_steam_name_from_steamid(log_steamid[0])

            players_online.append(log_character)
            player_info.append([players_online[0],""])
            #player_info.append([log_character,""])

        # Second step of joining the server, add the PlayerID assigned by the server to the player_info list
        elif "[session] Remote player added. Player handle: " in line:
            log_playerid = re.findall("Remote player added\. Player handle: 0\((\d+)\)", line)

            for i in range(len(player_info)):
                if player_info[i][0] == players_online[i]:
                    player_info[i][1] = log_playerid[0]

        #Third step of joining the server, add 'Joined' to the player_info list if the player fully logs into the server
        elif "logged in" in line:
            player_joined = "Unknown Player"
            log_playerid = re.findall("Player '0\((\d+)\)' logged in", line)

            for i in range(len(player_info)):
                if player_info[i][1] == log_playerid[0]:
                    player_joined = player_info[i][0]
                    player_info[i].append('Joined')

            discord_webook(f":green_square: {player_joined} joined the server")

        # If a player successfully joined the server, this is where they leave
        elif "[server] Remove Player" in line:
            log_character = re.findall(r"'([^']*)'", line)

            for i in range(len(player_info)):
                if player_info[i][1] == log_playerid[0]:
                    if player_info[i][2] == "Joined":
                        player_info.remove([player_info[i][0], player_info[i][1], player_info[i][2]])
            
            players_online.remove(log_character[0])
    
            discord_webook(f":red_square: {log_character[0]} left the server")

        # If a player unsuccessfully joined the server, this is where they leave
        elif "[session] Player removed. Player handle:" in line:
            log_playerid = re.findall("Player removed. Player handle: 0\((\d+)\)", line)

            for i in range(len(player_info)):
                if player_info[i][1] == log_playerid[0]:
                    if len(player_info) < 3:
                        player_not_joining = player_info[i][0]
                        players_online.remove(player_info[i][0])
                        player_info.remove([player_info[i][0], player_info[i][1]])

                        discord_webook(f":warning: {player_not_joining} unsuccessfully tried to join the server (Bad password?)")
        elif "[Session] 'HostOnline' (up)!" in line:
            discord_webook(f":white_check_mark: Server started")
        elif "[Session] 'HostOnline' (down)!" in line:
            discord_webook(f":octagonal_sign: Server shutdown")


if __name__ == "__main__":
    main()