import subprocess
import time
import datetime
import os
import threading

# Global variables
logcat_lock = threading.Lock()
logcat_process = None
logcat_file_handle = None

# Please change BASE_DIR according to your path 
BASE_DIR = "C:/Avisek/Automation/SM_custom_scripts/monkey_test"
LOG_DIR = os.path.join(BASE_DIR, "adb_logs")
MONKEY_DURATION_SECONDS = 120  # 5 minutes
INTERVAL_SECONDS = 60          # 1 minute
PACKAGE_LIST_FILE = os.path.join(BASE_DIR, "installed_packages.txt")
LOGCAT_FILE = os.path.join(LOG_DIR, "logcat_output_18_25.txt")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BASE_DIR, exist_ok=True)

# ADB command executer
def run_command(command):
    """Run a shell command and return stdout and stderr."""
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip(), result.stderr.strip()

# Fetching devices packages
def get_installed_packages():
    """Get list of installed packages on the device."""
    print("Fetching installed packages...")
    output, error = run_command("adb shell pm list packages")
    if error:
        print(f"Error fetching packages: {error}")
        return []
    packages = [line.split(":")[1] for line in output.splitlines()]
    with open(PACKAGE_LIST_FILE, 'w') as f:
        f.write("\n".join(packages))
    print("packages list", packages)
    # packages = ["com.android.contacts",
    #            "com.android.documentsui",
    #            "com.android.dialer",
    #            "com.qualcomm.qti.qmmi",
    #            "com.qualcomm.qti.sensors.qsensortest",
    #            "com.thundercomm.sensorui",
    #            "com.android.settings",
    #            "com.qualcomm.qti.watchsettings",
    #            "com.socialmobile.iotmdm"]
    return packages

# Dumping mem info
def dump_memory_info(phase):
    try:
        """Dump memory info using top command."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(LOG_DIR, f"top_{phase}_{timestamp}.txt")
        print(f"Dumping memory info ({phase}) to {filename}...")
        output, error = run_command("adb shell top -n 1")
        with open(filename, 'w') as f:
            f.write(output)
    except Exception as e:
        print("dump_memory_info exception", e)

# Capture log
def start_logcat_monitor():
    """Start and monitor adb logcat. Restart if the device disconnects/reboots."""
    def monitor():
        global logcat_process, logcat_file_handle
        while True:
            with logcat_lock:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = os.path.join(LOG_DIR, f"logcat_output_{timestamp}.txt")
                print(f"[logcat] Starting new capture: {log_filename}")
                logcat_file_handle = open(log_filename, "w")
                logcat_process = subprocess.Popen("adb logcat", shell=True, stdout=logcat_file_handle, stderr=subprocess.DEVNULL)

            logcat_process.wait()
            print("[logcat] Logcat process ended. Checking device connectivity...")

            while True:
                out, err = run_command("adb get-state")
                if "device" in out:
                    print("[logcat] Device is back. Restarting logcat.")
                    break
                print("[logcat] Waiting for device to reconnect...")
                time.sleep(5)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

def start_logcat():
    """Start adb logcat capturing in background process."""
    print("Starting logcat capture...")
    logcat_file_handle = open(LOGCAT_FILE, "w")
    process = subprocess.Popen("adb logcat", shell=True, stdout=logcat_file_handle, stderr=subprocess.DEVNULL)
    return process, logcat_file_handle

def stop_logcat(process, file_handle):
    """Stop adb logcat capturing."""
    print("Stopping logcat capture...")
    process.terminate()
    process.wait()
    file_handle.close()

# Configuring monkey command
def run_monkey_test(package):
    """Run monkey test on a package for 10 minutes."""
    print(f"Running monkey test on {package} for {MONKEY_DURATION_SECONDS // 60} minutes...")
    monkey_cmd = (
        f"adb shell monkey -p {package} -v 100000 --throttle 500 "
        "--ignore-crashes --ignore-timeouts --monitor-native-crashes "
        "--pct-touch 100 --pct-appswitch 0 --pct-anyevent 0"
    )
    process = subprocess.Popen(monkey_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(MONKEY_DURATION_SECONDS)
    process.terminate()
    process.wait()

def main():
    packages = get_installed_packages()
    if not packages:
        print("No packages found. Exiting.")
        return

    start_logcat_monitor()
    dump_memory_info("before")

    for count in range(3):  # 0 to 3 inclusive
        print(f"Starting iteration {count} over all packages...")
        for pkg in packages:
            run_monkey_test(pkg)
            dump_memory_info(f"interval_after_{pkg}_iteration{count}")
            print(f"Sleeping for {INTERVAL_SECONDS} seconds before next app...")
            time.sleep(INTERVAL_SECONDS)

    dump_memory_info("after")


if __name__ == "__main__":
    main()

