import sys
import time
import threading
import speedtest
import os
import json
import itertools

HISTORY_FILE = "network_history.json"
SETTINGS_FILE = "network_settings.json"

DEFAULT_SETTINGS = {
    "threads_quick": 2,
    "threads_full": 16
}

BANNER = r"""
 __                               ___    __                   __      
/\ \                             /\_ \  /\ \__               /\ \__   
\ \ \        ___     ___     __  \//\ \ \ \ ,_\    __    ____\ \ ,_\  
 \ \ \  __  / __`\  /'___\ /'__`\  \ \ \ \ \ \/  /'__`\ /',__\\ \ \/  
  \ \ \L\ \/\ \L\ \/\ \__//\ \L\.\_ \_\ \_\ \ \_/\  __//\__, `\\ \ \_ 
   \ \____/\ \____/\ \____\ \__/.\_\/\____\\ \__\ \____\/\____/ \ \__\
    \/___/  \/___/  \/____/\/__/\/_/\/____/ \/__/\/____/\/___/   \/__/
                                                                      
                                                                      
   _          __                                                      
 /' \       /'__`\                                                    
/\_, \     /\ \/\ \                                                   
\/_/\ \    \ \ \ \ \                                                  
   \ \ \  __\ \ \_\ \                                                 
    \ \_\/\_\\ \____/                                                 
     \/_/\/_/ \/___/                                                  

"""

COMMANDS_TEXT = """
\033[1;36m>> COMMANDS <<\033[0m

\033[1;33mlocaltest\033[0m

\033[1;33mlocaltest help\033[0m
    \033[90mcommands\033[0m Shows all commands.
    \033[90mflags\033[0m Shows all flags.

\033[1;33mlocaltest network\033[0m
    \033[90mrun\033[0m Runs the network scan. -fs is compatiable.
    \033[90mhistory\033[0m Shows the history of all your scans, locally.
    \033[90msettings\033[0m View or change settings for the Network tool.
"""

FLAGS_TEXT = """
\033[1;36m>> FLAGS <<\033[0m

\033[1;33m-fs\033[0m Fully and precisely use the current tool. Compatiable with: Network.
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

def show_network_header(): # holy shit styling no way :shocked:
    print("\n\033[1;34m╔══════════════════════════════╗\033[0m")
    print("\033[1;34m║\033[0m      \033[1;36mᯤ  Network Tool  ᯤ\033[0m      \033[1;34m║\033[0m")
    print("\033[1;34m╚══════════════════════════════╝\033[0m\n")

# next gen animated dots
def spinner(text, stop_event):
    spinner_cycle = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{text} {next(spinner_cycle)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + "    " * (len(text) + 2) + "\r")

# runs speed test :shocked:
def run_speed_test(full_scan=False):
    print(f"Starting {'full' if full_scan else 'quick'} network speed test...\n")

    try:
        stop_event = threading.Event()
        thread = threading.Thread(target=spinner, args=("Finding best server", stop_event))
        thread.start()

        st = speedtest.Speedtest()
        st.get_best_server()

        stop_event.set()
        thread.join()

        settings = load_settings()
        if full_scan:
            print("Full scan enabled: your scan will be more precise.\n")
            st.get_servers([])
            st.get_best_server()
            st._threads = settings.get("threads_full", 16)
        else:
            st._threads = settings.get("threads_quick", 2)

        stop_download = threading.Event()
        download_thread = threading.Thread(target=spinner, args=("Testing ↓ download speed", stop_download))
        download_thread.start()
        st.download()
        stop_download.set()
        download_thread.join()

        stop_upload = threading.Event()
        upload_thread = threading.Thread(target=spinner, args=("Testing ↑ upload speed", stop_upload))
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
        print("it looks like this is your first time here- use the command \033[1;33mlocaltest help\033[0m to get started!")
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
            show_network_header()
            print("\033[1;33mlocaltest network\033[0m")
            print("    \033[90mrun\033[0m Runs the network scan. -fs is compatiable.")
            print("    \033[90mhistory\033[0m Shows the history of all your scans, locally.")
            print("    \033[90msettings\033[0m View or change settings for the Network tool.")
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