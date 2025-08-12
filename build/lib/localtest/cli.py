import sys
import time
import threading
import speedtest
import os
import json

HISTORY_FILE = "network_history.json"
SETTINGS_FILE = "network_settings.json"

DEFAULT_SETTINGS = {
    "threads_quick": 2,
    "threads_full": 16
}

BANNER = r"""
 _       _____   _____   _____   _     
| |     |  _  | |  ___| |  _  | | |    
| |     | | | | | |     | |_| | | |    
| |___  | |_| | | |___  |  _  | | |___ 
|_____| |_____| |_____| |_/ \_| |_____| 

 _____   _____   _____   _____   
|_   _| |  ___| | ____| |_   _|  
  | |   | |__   |___  |   | |    
  | |   | |___   ___| |   | |    
  |_|   |_____| |_____|   |_|    v0.1
"""

COMMANDS_TEXT = """
>>  COMMANDS  <<

localtest help              |  Shows the complete list of available commands and flags.
               commands     |  Shows all commands.
               flags        |  Shows all flags.
localtest network           |  Shows the list of commands and flags available for the Network tool.
                  run       |  Run the network analyzer.
                  history   |  Shows the history of all your network scans.
                  settings  |  Shows all the settings you can change for the Network tool.
"""

FLAGS_TEXT = """
>>  FLAGS  <<

-fs  |  Fully and precisely use the tool.

"""

HELP_TEXT = COMMANDS_TEXT + FLAGS_TEXT

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def show_banner():
    print(BANNER)

def show_help():
    print(HELP_TEXT)

def show_commands():
    print(COMMANDS_TEXT)

def show_flags():
    print(FLAGS_TEXT)

# animated dots r cool !! unlike you (/j)
def animated_dots(text, stop_event):
    dots = ""
    while not stop_event.is_set():
        dots += "."
        if len(dots) > 3:
            dots = "."
        sys.stdout.write(f"\r{text}{dots}    ")
        sys.stdout.flush()
        time.sleep(0.4)
    sys.stdout.write("\r" + text + "... Done!\n")

# resuable loading bar?! :skulley: (ITS FAKE OMG)
def loading_bar(task, duration=3, length=20):
    print(f"{task}")
    for i in range(length + 1):
        percent = int((i / length) * 100)
        filled = "█"
        empty = "░" * (length - i)
        bar = f"[{filled}{empty}] {percent:3d}%"
        sys.stdout.write("\r" + bar + ' ' * 10)
        sys.stdout.flush()
        time.sleep(duration / (length * 2))
    print("")

# runs speed test :shocked:
def run_speed_test(full_scan=False):
    print(f"Starting {'full' if full_scan else 'quick'} network speed test...\n")

    try:
        stop_event = threading.Event()
        thread = threading.Thread(target=animated_dots, args=("Finding best server", stop_event))
        thread.start()

        st = speedtest.Speedtest()
        st.get_best_server()

        stop_event.set()
        thread.join()

        print("\nBest server found!\n")

        if full_scan:
            print("Full scan enabled: your scan will be more precise.\n")
            st.get_servers([])
            st.get_best_server()
            st._threads = 16
        else:
            st._threads = 2

        stop_download = threading.Event()
        download_thread = threading.Thread(target=animated_dots, args=("Testing ↓ download speed", stop_download))
        download_thread.start()
        st.download()
        stop_download.set()
        download_thread.join()

        stop_upload = threading.Event()
        upload_thread = threading.Thread(target=animated_dots, args=("Testing ↑ upload speed", stop_upload))
        upload_thread.start()
        st.upload()
        stop_upload.set()
        upload_thread.join()

        results = st.results.dict()
        download_mbps = results['download'] / 1_000_000
        upload_mbps = results['upload'] / 1_000_000
        ping = results['ping']
        isp = results.get('client', {}).get('isp', 'Unknown ISP')

        print("\n--- Speed Test Results ---")
        print(f"ISP: {isp}")
        print(f"Ping: {ping:.2f} ms")
        print(f"Download: {download_mbps:.2f} Mbps")
        print(f"Upload: {upload_mbps:.2f} Mbps\n")

        history = load_history()
        history.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "full_scan": full_scan,
            "isp": isp,
            "ping": round(ping, 2),
            "download_mbps": round(download_mbps, 2),
            "upload_mbps": round(upload_mbps, 2)
        })
        save_history(history)

    except Exception as e:
        print(f"Error during speed test: {e}")

def main():
    args = sys.argv[1:]

    if not args:
        show_banner()
        show_help()
        return 
    elif args[0] == "help":
        if len(args) == 1:
            show_help()
            return
        elif args[1] == "commands":
            show_commands()
            return
        elif args[1] == "flags":
            show_flags()
            return
        else:
            print(f"Unknown help subcommand: {args[1]}")
            return
    elif args[0] == "network":
        if len(args) == 1:
            print("ᯤ  Network Tool  ᯤ")
            print("localtest network run       |  Run the network analyzer")
            print("                  history   |  Shows the history of all your network scans. ")
            print("                  settings  |  Shows all the settings you can change for the Network tool.")
            return
        elif args[1] == "run":
            full_scan = "-fs" in args or "--fullscan" in args
            run_speed_test(full_scan=full_scan)
            return
        elif args[1] == "history":
            history = load_history()
            if not history:
                print("No history found. Start Localhosting by using the command 'localtest network run'!")
            else:
                for entry in history:
                    print(f"[{entry['timestamp']}] "
                          f"{'FULL' if entry['full_scan'] else 'QUICK'} | "
                          f"ISP: {entry['isp']} | Ping: {entry['ping']} ms | "
                          f"↓ {entry['download_mbps']} Mbps | ↑ {entry['upload_mbps']} Mbps")
                return
            return
        elif args[1] == "settings":
            settings = load_settings()
            if len(args) == 2:
                print("Current settings:")
                for k, v in settings.items():
                    print(f"  {k}: {v}")
            elif len(args) == 4 and args[2] == "set":
                key, value = args[3].split("=")
                if key in settings:
                    settings[key] = int(value)
                    save_settings(settings)
                    print(f"Setting '{key}' updated to {value}.")
                else:
                    print(f"Unknown setting: {key}")
            else:
                print("Usage:\n  localtest network settings\n  localtest network settings set threads_quick=4")
            return
        else:
            print(f"Unknown network subcommand: {args[1]}")
            return
    
    print(f"Unknown command: {args[0]}")