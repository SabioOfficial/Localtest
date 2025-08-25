import sys
import time
import threading
import speedtest
import os
import json
import itertools
import signal
import subprocess
import platform
import re

if os.name == "nt":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    kernel32.SetConsoleMode(handle, mode.value | 0x0004)

HISTORY_FILE = "network_history.json"
SETTINGS_FILE = "network_settings.json"

DEFAULT_SETTINGS = {
    "threads_quick": 2,
    "threads_full": 16,
}

active_stop_events = []

BANNER = r"""
 __                               ___    __                   __      
/\ \                             /\_ \  /\ \__               /\ \__   
\ \ \        ___     ___     __  \//\ \ \ \ ,_\    __    ____\ \ ,_\  
 \ \ \  __  / __`\  /'___\ /'__`\  \ \ \ \ \ \/  /'__`\ /',__\\ \ \/  
  \ \ \L\ \/\ \L\ \/\ \__//\ \L\.\_ \_\ \_\ \ \_/\  __//\__, `\\ \ \_ 
   \ \____/\ \____/\ \____\ \__/.\_\/\____\\ \__\ \____\/\____/ \ \__\
    \/___/  \/___/  \/____/\/__/\/_/\/____/ \/__/\/____/\/___/   \/__/
                                                                      
                                                                      
   _        _                                                         
 /' \     /' \                                                        
/\_, \   /\_, \                                                       
\/_/\ \  \/_/\ \                                                      
   \ \ \  __\ \ \                                                     
    \ \_\/\_\\ \_\                                                    
     \/_/\/_/ \/_/                                                    

""" # used https://www.asciiart.eu/text-to-ascii-art Larry 3D font

COMMANDS_TEXT = """
\033[1;36m>> COMMANDS <<\033[0m

\033[1;33mlocaltest\033[0m

\033[1;33mlocaltest help\033[0m
    \033[90mcommands\033[0m Shows all commands.
    \033[90mflags\033[0m Shows all flags.

\033[1;33mlocaltest update\033[0m Update Localtest to the latest version.

\033[1;33mlocaltest network\033[0m
    \033[90mrun\033[0m Runs the network scan. -fs is compatiable.
    \033[90mhistory\033[0m Shows the history of all your scans, locally.
    \033[90msettings\033[0m View or change settings for the Network tool.
    \033[90mimprove\033[0m Running this command will improve your network speeds. -a is compatiable.
"""

FLAGS_TEXT = """
\033[1;36m>> FLAGS <<\033[0m

\033[1;33m-fs\033[0m Fully and precisely use the current tool. Compatiable with: Network RUN.
\033[1;33m-a\033[0m Apply. Compatiable with: Network IMPROVE.
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

def handle_exit(signum, frame):
    print("\n\033[1;31m[!] Process interrupted by user. Exiting...\033[0m")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

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

# next gen animated dots :heavysob-random:
def spinner(text, stop_event):
    spinner_cycle = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{text} {next(spinner_cycle)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(text) + 2) + "\r")

# i leaked my ip in devlogs twice... this is why i'm masking ips
def mask_ip(ip):
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:1] + ["x" * len(parts[1]), "x" * len(parts[2]), "x" * len(parts[3])])
    return ".".join("x" * len(part) for part in parts)

# runs speed test :shocked:
def run_speed_test(full_scan=False):
    print(f"Starting {'full' if full_scan else 'quick'} network speed test...\n")
    st = speedtest.Speedtest()
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=("Finding best server", stop_event))
    spinner_thread.start()

    try:
        st.get_best_server()
    finally:
        stop_event.set()
        spinner_thread.join()

    settings = load_settings()
    st._threads = settings.get("threads_full" if full_scan else "threads_quick", 16 if full_scan else 2)

    download_result = [None]
    stop_download = threading.Event()
    def download_worker():
        try:
            download_result[0] = st.download()
        finally:
            stop_download.set()

    download_thread = threading.Thread(target=download_worker)
    spinner_thread = threading.Thread(target=spinner, args=("Testing ↓ download speed", stop_download))
    download_thread.start()
    spinner_thread.start()
    download_thread.join()
    spinner_thread.join()

    upload_result = [None]
    stop_upload = threading.Event()
    def upload_worker():
        try:
            upload_result[0] = st.upload()
        finally:
            stop_upload.set()

    upload_thread = threading.Thread(target=upload_worker)
    spinner_thread = threading.Thread(target=spinner, args=("Testing ↑ upload speed", stop_upload))
    upload_thread.start()
    spinner_thread.start()
    upload_thread.join()
    spinner_thread.join()

    results = st.results.dict()
    download_mbps = results['download'] / 1_000_000
    upload_mbps = results['upload'] / 1_000_000
    ping = results['ping']
    isp = results.get('client', {}).get('isp', 'Unknown ISP')

    print("\n\033[1;32m--- Speed Test Results ---\033[0m")
    print(f"\033[1;33mISP:\033[0m {isp}")
    print(f"\033[1;33mPing:\033[0m {ping:.2f} ms")
    print(f"\033[1;33mDownload:\033[0m {download_mbps:.2f} Mbps")
    print(f"\033[1;33mUpload:\033[0m {upload_mbps:.2f} Mbps\n")

    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "full_scan": full_scan,
        "isp": isp,
        "ping": round(ping, 2),
        "download_mbps": round(download_mbps, 2),
        "upload_mbps": round(upload_mbps, 2)
    }

    history = load_history()
    history.append(entry)
    save_history(history)

    return entry

def run_ping(host="8.8.8.8", count=4): # oh no google's going to googsteale your data
    os_name = platform.system().lower()
    if os_name == "windows":
        cmd = ["ping", "-n", str(count), host]
    else:
        cmd = ["ping", "-c", str(count), host]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = p.stdout
        packet_loss = None
        avg = None

        m_loss = re.search(r"Lost = \d+ $begin:math:text$(\\d+)% loss$end:math:text$", out)
        if m_loss:
            packet_loss = float(m_loss.group(1))
        else:
            m_loss_unix = re.search(r"(\d+)% packet loss", out)
            if m_loss_unix:
                packet_loss = float(m_loss_unix.group(1))

        m_avg_win = re.search(r"Average = (\d+)ms", out)
        if m_avg_win:
            avg = float(m_avg_win.group(1))
        else:
            m_avg_unix = re.search(r"rtt .* = [\d\.]+/([\d\.]+)/", out)
            if m_avg_unix:
                avg = float(m_avg_unix.group(1))
        
        return {"raw": out, "packet_loss_percent": packet_loss, "avg_ms": avg}
    except Exception as e:
        return {"error": str(e)}

def get_dns_servers():
    os_name = platform.system().lower()
    servers = []
    try:
        if os_name == "windows":
            p = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True)
            matches = re.findall(r"DNS Servers[.\s:]*([\d\.\s\r\n:]+)", p.stdout)
            if matches:
                raw = matches[0].strip().splitlines() # please do not screenshot that out of context i beg
                for line in raw:
                    ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if ip_match:
                        servers.append(ip_match.group(1))
            else:
                lines = p.stdout.splitlines()
                for i, line in enumerate(lines):
                    if "DNS Servers" in line:
                        j = i + 1
                        while j < len(lines) and lines[j].strip():
                            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", lines[j])
                            if ip_match:
                                servers.append(ip_match.group(1))
                            j += 1
        else:
            if os.path.exists("/etc/resolv.conf"):
                with open("/etc/resolv.conf", "r") as f:
                    for ln in f:
                        if ln.strip().startswith("nameserver"):
                            parts = ln.split()
                            if len(parts) >= 2:
                                servers.append(parts[1].strip())
            if not servers:
                p = subprocess.run(["resolvectl", "status"], capture_output=True, text=True)
                if p.returncode == 0:
                    servers += re.findall(r"Current DNS Server: (\d+\.\d+\.\d+\.\d+)", p.stdout)
    except Exception:
        pass
    return servers

def build_suggestions(metrics):
    suggestions = []
    download = metrics.get("download_mbps")
    upload = metrics.get("upload_mbps")
    ping = metrics.get("ping")
    packet_loss = metrics.get("packet_loss_percent")

    suggestions.append("1) Used a wired (Ethernet) connection where possible. It's the best way to reduce latency.")
    suggestions.append("2) Reboot your modem or router if possible. Most issues are resolved by a quick reboot of network gear.")
    suggestions.append("3) Ensure other devices or apps aren't eating your connection (cloud backups, torrents, streaming).")

    if download is not None:
        if download < 5:
            suggestions.append("Download speed is very low - check if you're on the correct ISP plan or contact your ISP. Also check for heavy background uploads.")
        elif download < 50:
            suggestions.append("Download speed is moderate - if you expected higher, try moving closer to the router, switching Wi-Fi bands (5GHz), or using Ethernet.")
        else:
            suggestions.append("Download speed looks good.")

    if ping is not None:
        if ping > 150:
            suggestions.append("High ping detected - try switching to a closer server, use wired connection, or check for VPNs and background processes causing latency.")
        elif ping > 60:
            suggestions.append("Moderate latency - wired connection and moving your router to an open area may help.")
        else:
            suggestions.append("Latency is good.")

    if packet_loss is not None:
        if packet_loss > 1:
            suggestions.append(f"Packet loss detected ({packet_loss}%) - this often indicates Wi-Fi interference, bad cabling, or upstream ISP issues.")
        else:
            suggestions.append("No significant packet loss detected.")

    dns = metrics.get("dns_servers", [])
    if dns:
        masked_dns = [mask_ip(d) for d in dns]
        suggestions.append(f"Your DNS servers: {', '.join(masked_dns)} - consider using reliable DNS providers like 1.1.1.1 (Cloudflare), 8.8.8.8 (Google) if you have DNS resolution issues.")
    
    suggestions.append("Advanced: Make sure you update router firmware, ensure drivers for your network network adapter are up-to-date, consider changing QoS settings on your router, or try changing your router channel to reduce Wi-Fi interference.")
    suggestions.append("If multiple tests show consistent low throughput, contact your ISP and provide the speed test timestamps and results.")

    return suggestions

def build_fix_commands():
    os_name = platform.system().lower()
    commands = []
    if os_name == "windows":
        commands = [
            ("Flush DNS cache (Windows)", "ipconfig /flushdns"),
            ("Release DHCP (Windows)", "ipconfig /release"),
            ("Renew DHCP (Windows)", "ipconfig /renew"),
        ] # afaik these are safe to run? ima get sued :skulk:
    elif os_name == "darwin":
        # stinky macOS
        commands = [
            ("Flush DNS (macOS)", "sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder"),
            ("Restart network service (macOS)", "sudo ifconfig en0 down; sleep 1; sudo ifconfig en0 up"),
        ]
    else:
        # assume Linux-ish os
        commands = [
            ("Flush DNS (systemd-resolved)", "sudo systemd-resolve --flush-caches"),
            ("Restart NetworkManager (Linux)", "sudo systemctl restart NetworkManager"),
            ("Restart network interface (Linux) - may vary", "sudo ip link set $(ip route get 8.8.8.8 | awk '{print $5; exit}') down; sleep 1; sudo ip link set $(ip route get 8.8.8.8 | awk '{print $5; exit}') up"),
        ]
    return commands

def improve_network(apply=False):
    print("\n\033[1;34m--- Running network improve diagnostic ---\033[0m\n")
    baseline = run_speed_test(full_scan=False)
    if not baseline:
        print("Couldn't get baseline speed test; aborting improve routine.")
        return
    
    ping_results = run_ping()
    dns_servers = get_dns_servers()
    masked_dns = [mask_ip(d) for d in dns_servers]

    metrics = {
        "download_mbps": baseline.get("download_mbps"),
        "upload_mbps": baseline.get("upload_mbps"),
        "ping": baseline.get("ping"),
        "isp": baseline.get("isp"),
        "packet_loss_percent": None,
        "dns_servers": masked_dns
    }
    if ping_results and "avg_ms" in ping_results:
        metrics["packet_loss_percent"] = ping_results.get("packet_loss_percent")
        metrics["ping"] = ping_results.get("avg_ms") or metrics["ping"]

    print("\033[1;32m--- Diagnostics ---\033[0m")
    print(f"ISP: {metrics.get('isp')}")
    print(f"Download: {metrics.get('download_mbps'):.2f} Mbps")
    print(f"Upload: {metrics.get('upload_mbps'):.2f} Mbps")
    if metrics.get("ping") is not None:
        print(f"Ping (avg): {metrics.get('ping'):.2f} ms")
    if metrics.get("packet_loss_percent") is not None:
        print(f"Packet loss: {metrics.get('packet_loss_percent')}%")
    if dns_servers:
        print(f"DNS servers: {', '.join(masked_dns)}")
    else:
        print("DNS servers: Could not detect")
    
    print("\n\033[1;32m--- Suggestions to improve speeds ---\033[0m")
    suggestions = build_suggestions(metrics)
    for s in suggestions:
        print(f"- {s}")

    if apply:
        print("\n\033[1;33mApply mode requested. The script will attempt common fixes (may require admin/sudo).\033[0m")
        fixes = build_fix_commands()
        print("Planned actions:")
        for i, (desc, cmd) in enumerate(fixes, start=1):
            print(f"  {i}. {desc} -> {cmd}")

        confirm = input("\nProceed to run the above commands? This may temporarily disconnect your network. [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborting apply actions.")
            return
        
        for desc, cmd in fixes:
            print(f"\n\033[1;34mRunning:\033[0m {desc}\n-> {cmd}")
            try:
                p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if p.returncode == 0:
                    print(f"[OK] {desc} completed.")
                    if p.stdout:
                        print(p.stdout.strip())
                else:
                    print(f"[WARN] {desc} returned non-zero exit code {p.returncode}.")
                    if p.stdout:
                        print("STDOUT:", p.stdout.strip())
                    if p.stderr:
                        print("STDERR:", p.stderr.strip())
            except Exception as e:
                print(f"[ERROR] Failed to run {desc}: {e}")

        print("\n\033[1;32mApply actions completed. Re-running a quick speed test to show updated results...\033[0m")
        time.sleep(2)
        run_speed_test(full_scan=False)
    else:
        print("\nTo automatically try common fixes, re-run with the flag \033[1;33m-a\033[0m or \033[1;33m--apply\033[0m (you will be asked to confirm before any changes).")

def main():
    args = sys.argv[1:]

    if not args:
        show_banner()
        print("use \033[1;33mlocaltest help\033[0m to get started!")
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
        elif args[1] == "improve":
            apply_flag = ("-a" in args) or ("--apply" in args)
            improve_network(apply=apply_flag)
            return
        else:
            print(f"Unknown network subcommand: {args[1]}")
            return
    
    print(f"Unknown command: {args[0]}")