import sys
import time
import threading
import speedtest

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

    except Exception as e:
        print(f"Error during speed test: {e}")

def main():
    args = sys.argv[1:]

    if not args:
        show_banner()
        show_help()
        return
    
    if args[0] == "help":
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

    if args[0] == "network":
        if len(args) == 1:
            print("ᯤ  Network Tool  ᯤ")
            print("localtest network run       |  Run the network analyzer")
            print("                  history   |  Shows the history of all your network scans. ")
            print("                  settings  |  Shows all the settings you can change for the Network tool.")
            return
        elif args[1] == "run":
            full_scan = "-f" in args or "--full" in args
            run_speed_test(full_scan=full_scan)
            return
        else:
            print(f"Unknown network subcommand: {args[1]}")
            return
    
    print(f"Unknwon command: {args[0]}")