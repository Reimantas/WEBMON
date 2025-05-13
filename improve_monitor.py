import subprocess
import mysql.connector
from datetime import datetime
import os
import signal
import time
import shlex
import random # <-- Pridėtas random modulis

# --- Konfigūracija ---
# Atsitiktinių prievadų diapazonas
PORT_RANGE_START = 55000
PORT_RANGE_END = 65000

# !! SVARBU !! Įsitikink, kad čia įrašytas Tavo TINKLO SĄSAJOS PAVADINIMAS !!
NETWORK_INTERFACE = 'enp0s3' 

# Laikino pcap failo pavadinimo šablonas
PCAP_FILE_TEMPLATE = 'capture_{port}.pcap' # Naudosim port'ą pavadinime
# Kiek laiko (sekundėmis) laukti tcpdump pabaigos po signalo
TCPDUMP_WAIT_TIMEOUT = 5
# Curl prisijungimo laukimo limitas
CURL_CONNECT_TIMEOUT = 10
# Curl bendras laukimo limitas
CURL_TOTAL_TIMEOUT = 30

# Hardcoded websites that should always be monitored
HARDCODED_WEBSITES = [
    "https://delfi.lt",
    "https://google.com"
]
# --- Konfigūracijos pabaiga ---

def run_check_with_tcpdump(url, interface, local_port, pcap_file):
    """
    Vykdo svetainės pasiekiamumo patikrinimą su curl, tuo pačiu metu
    su tcpdump gaudo srautą ir skaičiuoja 'Duplicate ACK' paketus.
    Naudoja nurodytą local_port ir pcap_file.

    Grąžina: tuple (curl_metrics_string, duplicate_ack_count)
             duplicate_ack_count yra -1, jei įvyko klaida gaudant/analizuojant.
    """
    tcpdump_proc = None
    curl_metrics_str = "time_namelookup:0,time_connect:0,time_appconnect:0,time_pretransfer:0,time_redirect:0,time_starttransfer:0,time_total:0,speed_download:0,speed_upload:0,size_download:0"
    duplicate_ack_count = -1

    # Patikrinam ar nurodyta sąsaja nėra placeholder'is (nors jau pakeitei, bet paliekam)
    if interface == 'PAKEISK_MANE':
         print(f"ERROR: Network interface is not set in the script! Please edit NETWORK_INTERFACE variable.")
         return curl_metrics_str, duplicate_ack_count

    # Paruošiam tcpdump komandą
    tcpdump_command = f"tcpdump -i {interface} -n -s0 -w {pcap_file} 'tcp port {local_port}'"
    tcpdump_args = shlex.split(tcpdump_command)

    # Paruošiam curl komandą
    curl_w_format = "time_namelookup:%{time_namelookup},time_connect:%{time_connect},time_appconnect:%{time_appconnect},time_pretransfer:%{time_pretransfer},time_redirect:%{time_redirect},time_starttransfer:%{time_starttransfer},time_total:%{time_total},speed_download:%{speed_download},speed_upload:%{speed_upload},size_download:%{size_download}"
    curl_command = [
        'curl',
        '--local-port', str(local_port),
        '--connect-timeout', str(CURL_CONNECT_TIMEOUT),
        '-w', curl_w_format,
        '-s',
        '-o', '/dev/null',
        url
    ]

    try:
        # --- Paleidžiam procesus ---
        print(f"Starting tcpdump: {' '.join(tcpdump_args)}")
        tcpdump_proc = subprocess.Popen(tcpdump_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.5)
        if tcpdump_proc.poll() is not None:
            stderr_output = tcpdump_proc.stderr.read().decode(errors='ignore')
            print(f"Error starting tcpdump for {url}. Process exited with code {tcpdump_proc.returncode}. Stderr: {stderr_output}")

        print(f"Running curl: {' '.join(curl_command)}")
        curl_result = subprocess.run(curl_command, capture_output=True, text=True, timeout=CURL_TOTAL_TIMEOUT)
        if curl_result.returncode == 0:
             curl_metrics_str = curl_result.stdout.strip()
        else:
             print(f"Curl command failed for {url} with code {curl_result.returncode}. Stderr: {curl_result.stderr.strip()}")

    except FileNotFoundError:
        print(f"Error: tcpdump or curl command not found. Are they installed and in PATH?")
        duplicate_ack_count = -1
    except subprocess.TimeoutExpired:
        print(f"Curl timeout expired for {url}")
    except Exception as e:
        print(f"An unexpected error occurred during tcpdump/curl execution for {url}: {e}")
        if tcpdump_proc and tcpdump_proc.poll() is None:
            try:
                print(f"Terminating tcpdump process (PID: {tcpdump_proc.pid}) due to error...")
                tcpdump_proc.terminate()
                tcpdump_proc.wait(timeout=TCPDUMP_WAIT_TIMEOUT/2)
            except subprocess.TimeoutExpired:
                print(f"Tcpdump did not terminate gracefully, killing...")
                tcpdump_proc.kill()
            except Exception as kill_e:
                 print(f"Error trying to stop tcpdump after error: {kill_e}")
        duplicate_ack_count = -1
    finally:
        # --- Sustabdom tcpdump ---
        if tcpdump_proc and tcpdump_proc.poll() is None:
            print(f"Stopping tcpdump process (PID: {tcpdump_proc.pid})...")
            try:
                 tcpdump_proc.send_signal(signal.SIGINT)
                 tcpdump_proc.wait(timeout=TCPDUMP_WAIT_TIMEOUT)
                 print("Tcpdump stopped gracefully.")
            except subprocess.TimeoutExpired:
                print(f"Tcpdump did not stop within {TCPDUMP_WAIT_TIMEOUT}s, killing process...")
                tcpdump_proc.kill()
                time.sleep(0.5)
            except Exception as stop_e:
                 print(f"Error trying to stop tcpdump: {stop_e}")

        # --- Analizuojam pcap failą ---
        if os.path.exists(pcap_file):
            print(f"Analyzing pcap file: {pcap_file}")
            p1 = p2 = p3 = None
            try:
                cmd1 = ['tcpdump', '-n', '-r', pcap_file]
                cmd2 = ['grep', 'Dup ACK']
                cmd3 = ['wc', '-l']

                print(f"  Running: {' '.join(cmd1)} | {' '.join(cmd2)} | {' '.join(cmd3)}")

                p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if p1.stdout: p1.stdout.close()

                p3 = subprocess.Popen(cmd3, stdin=p2.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if p2.stdout: p2.stdout.close()

                stdout, stderr3 = p3.communicate()
                stderr2 = p2.stderr.read() if p2.stderr else b''
                stderr1 = p1.stderr.read() if p1.stderr else b''

                p3_ret = p3.wait()
                p2_ret = p2.wait()
                p1_ret = p1.wait()

                print(f"  Analysis process return codes: tcpdump_read={p1_ret}, grep={p2_ret}, wc={p3_ret}")

                analysis_error = False
                if p1_ret != 0:
                    print(f"  Error reading pcap file (tcpdump exit code {p1_ret}). Stderr: {stderr1.decode(errors='ignore')}")
                    analysis_error = True
                if p2_ret not in [0, 1]:
                    print(f"  Error running grep (exit code {p2_ret}). Stderr: {stderr2.decode(errors='ignore')}")
                    analysis_error = True
                if p3_ret != 0:
                    print(f"  Error running wc (exit code {p3_ret}). Stderr: {stderr3.decode(errors='ignore')}")
                    analysis_error = True

                if not analysis_error:
                    if p2_ret == 0:
                        try:
                            duplicate_ack_count = int(stdout.strip())
                        except ValueError:
                            print(f"  Could not parse duplicate ACK count from wc output: {stdout.strip()}")
                            duplicate_ack_count = -1
                    elif p2_ret == 1:
                         duplicate_ack_count = 0
                         print("  Grep found no 'Dup ACK' lines.")
                else:
                     duplicate_ack_count = -1

            except FileNotFoundError as fnf_err:
                 print(f"  Error during pcap analysis: command not found ({fnf_err.filename}). Is tcpdump/grep/wc installed?")
                 duplicate_ack_count = -1
            except Exception as analysis_e:
                print(f"  An error occurred during pcap analysis for {url}: {analysis_e}")
                duplicate_ack_count = -1

        else:
            if tcpdump_proc is not None:
                 print(f"Pcap file {pcap_file} not found for analysis (maybe tcpdump failed to capture?).")
            duplicate_ack_count = -1

        # --- PCAP failo ištrynimas ---
        if os.path.exists(pcap_file):
            print(f"Removing pcap file: {pcap_file}")
            try:
                os.remove(pcap_file)
            except OSError as remove_e:
                print(f"Error removing pcap file {pcap_file}: {remove_e}")

    return curl_metrics_str, duplicate_ack_count

def store_data(db_config, url, metrics, duplicate_acks):
    """ Store metrics and duplicate ACK count in the database """
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS website_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY, url VARCHAR(255) UNIQUE,
                time_namelookup FLOAT, time_connect FLOAT, time_appconnect FLOAT,
                time_pretransfer FLOAT, time_redirect FLOAT, time_starttransfer FLOAT,
                time_total FLOAT, speed_download FLOAT, speed_upload FLOAT,
                size_download FLOAT, duplicate_acks INT DEFAULT 0, timestamp DATETIME
            )
        """)
        data = {}
        valid_keys = ['time_namelookup', 'time_connect', 'time_appconnect', 'time_pretransfer', 'time_redirect', 'time_starttransfer', 'time_total', 'speed_download', 'speed_upload', 'size_download']
        for key in valid_keys: data[key] = 0.0
        for item in metrics.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                if k in valid_keys:
                    try: data[k] = float(v)
                    except ValueError: data[k] = 0.0
        data['url'] = url
        data['timestamp'] = datetime.now()
        data['duplicate_acks'] = duplicate_acks if duplicate_acks >= 0 else 0
        sql = """
            INSERT INTO website_metrics (
                url, time_namelookup, time_connect, time_appconnect, time_pretransfer,
                time_redirect, time_starttransfer, time_total, speed_download, speed_upload,
                size_download, duplicate_acks, timestamp
            ) VALUES (
                %(url)s, %(time_namelookup)s, %(time_connect)s, %(time_appconnect)s, %(time_pretransfer)s,
                %(time_redirect)s, %(time_starttransfer)s, %(time_total)s, %(speed_download)s, %(speed_upload)s,
                %(size_download)s, %(duplicate_acks)s, %(timestamp)s
            )
            ON DUPLICATE KEY UPDATE
                time_namelookup = VALUES(time_namelookup), time_connect = VALUES(time_connect),
                time_appconnect = VALUES(time_appconnect), time_pretransfer = VALUES(time_pretransfer),
                time_redirect = VALUES(time_redirect), time_starttransfer = VALUES(time_starttransfer),
                time_total = VALUES(time_total), speed_download = VALUES(speed_download),
                speed_upload = VALUES(speed_upload), size_download = VALUES(size_download),
                duplicate_acks = VALUES(duplicate_acks), timestamp = VALUES(timestamp)
        """
        cursor.execute(sql, data)
        connection.commit()
    except mysql.connector.Error as err: print(f"Database error while storing data for {url}: {err}")
    except Exception as e: print(f"Unexpected error storing data for {url}: {e}")
    finally:
        if connection and connection.is_connected():
             cursor.close()
             connection.close()

def fetch_websites(db_config):
    """ Fetch websites but ensure only HARDCODED ones + new ones are included. """
    connection = None
    db_websites = []
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_websites (
                id INT AUTO_INCREMENT PRIMARY KEY, url VARCHAR(255) UNIQUE, added_on DATETIME
            )
        """)
        cursor.execute("SELECT url FROM monitored_websites")
        db_websites = [row[0] for row in cursor.fetchall() if row and len(row) > 0]
    except mysql.connector.Error as err: print(f"Database error fetching websites: {err}")
    except Exception as e: print(f"Unexpected error fetching websites: {e}")
    finally:
         if connection and connection.is_connected():
            cursor.close()
            connection.close()
    return list(set(HARDCODED_WEBSITES + db_websites))

# --- PAGRINDINĖ VYKDYMO DALIS (su atsitiktiniais prievadais) ---
if __name__ == '__main__':
    # Database configuration
    db_config = {
        'user': 'monitor_user',
        'password': 'monitor',
        'host': 'localhost', # Arba '127.0.0.1', jei 'localhost' kėlė problemų
        'database': 'website_monitor'
    }

    websites = fetch_websites(db_config)

    if not websites:
        print("No websites found in the database or hardcoded list.")
    else:
        print(f"--- Starting Monitoring Cycle ---")
        if NETWORK_INTERFACE == 'PAKEISK_MANE':
             print("!!!!!! ERROR: NETWORK_INTERFACE variable is not set correctly in improve_monitor.py !!!!!!")
             print("!!!!!! Please edit the script and set the correct network interface name. Exiting. !!!!!!")
             exit(1)

        print(f"Using Network Interface: {NETWORK_INTERFACE}")
        print(f"Using Curl Random Local Port Range: {PORT_RANGE_START}-{PORT_RANGE_END}") # <-- Pakeistas pranešimas
        print(f"Using PCAP file template: {PCAP_FILE_TEMPLATE}") # <-- Pakeistas pranešimas
        print(f"Websites to monitor: {', '.join(websites)}")
        print("-" * 30)

        # Einam per svetaines
        for site in websites:
            # Kiekvienai svetainei generuojam ATSITIKTINĮ prievadą iš nurodyto diapazono
            current_port = random.randint(PORT_RANGE_START, PORT_RANGE_END)
            # Sukuriam unikalų pcap failo pavadinimą pagal prievadą
            current_pcap_file = PCAP_FILE_TEMPLATE.format(port=current_port)

            print(f"Checking {site} (using random port {current_port})...") # <-- Pakeistas pranešimas
            # Kviečiam funkciją su dabartiniu prievadu ir pcap failu
            metrics_str, ack_count = run_check_with_tcpdump(site, interface=NETWORK_INTERFACE, local_port=current_port, pcap_file=current_pcap_file)

            print(f"  Curl Metrics: {metrics_str}")
            if ack_count >= 0:
                 print(f"  Duplicate ACK Count: {ack_count}")
            else:
                 print(f"  Duplicate ACK Count: Error during capture/analysis")

            # Saugom duomenis
            store_data(db_config, site, metrics_str, ack_count)
            print(f"Finished checking {site}.")
            print("-" * 10)

        print("--- Monitoring Cycle Completed ---")
