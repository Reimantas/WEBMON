from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import subprocess
from datetime import datetime

app = Flask(__name__)

# Database configuration
db_config = {
    'user': 'monitor_user',
    'password': 'monitor',
    'host': 'localhost',
    'database': 'website_monitor'
}

def run_curl_and_store(url):
    """ Run curl command to fetch website metrics and store them in the database. """
    command = [
        'curl',
        '-w', "time_namelookup:%{time_namelookup},time_connect:%{time_connect},time_appconnect:%{time_appconnect},time_pretransfer:%{time_pretransfer},time_redirect:%{time_redirect},time_starttransfer:%{time_starttransfer},time_total:%{time_total},speed_download:%{speed_download},speed_upload:%{speed_upload},size_download:%{size_download}",
        '-s',
        '-o', '/dev/null',  # Discard the body output
        url
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        metrics = result.stdout.strip()
        
        # Store metrics in the database
        store_metrics(url, metrics)
    except subprocess.TimeoutExpired:
        print(f"Timeout expired for {url}")
    except Exception as e:
        print(f"Error fetching metrics for {url}: {e}")

def store_metrics(url, metrics):
    """ Parse and store website metrics in the database. """
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS website_metrics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url VARCHAR(255) UNIQUE,
            time_namelookup FLOAT,
            time_connect FLOAT,
            time_appconnect FLOAT,
            time_pretransfer FLOAT,
            time_redirect FLOAT,
            time_starttransfer FLOAT,
            time_total FLOAT,
            speed_download FLOAT,
            speed_upload FLOAT,
            size_download FLOAT,
            timestamp DATETIME
        )
    """)

    # Safely parse metrics
    data = {}
    for item in metrics.split(","):
        if ":" in item:
            k, v = item.split(":", 1)
            try:
                data[k] = float(v)
            except ValueError:
                data[k] = 0.0  # Default to 0 if conversion fails

    data['url'] = url
    data['timestamp'] = datetime.now()

    cursor.execute("""
        INSERT INTO website_metrics (
            url, time_namelookup, time_connect, time_appconnect, time_pretransfer, 
            time_redirect, time_starttransfer, time_total, speed_download, speed_upload, 
            size_download, timestamp
        ) VALUES (%(url)s, %(time_namelookup)s, %(time_connect)s, %(time_appconnect)s, %(time_pretransfer)s,
                  %(time_redirect)s, %(time_starttransfer)s, %(time_total)s, %(speed_download)s, %(speed_upload)s,
                  %(size_download)s, %(timestamp)s)
        ON DUPLICATE KEY UPDATE 
            time_namelookup = VALUES(time_namelookup),
            time_connect = VALUES(time_connect),
            time_appconnect = VALUES(time_appconnect),
            time_pretransfer = VALUES(time_pretransfer),
            time_redirect = VALUES(time_redirect),
            time_starttransfer = VALUES(time_starttransfer),
            time_total = VALUES(time_total),
            speed_download = VALUES(speed_download),
            speed_upload = VALUES(speed_upload),
            size_download = VALUES(size_download),
            timestamp = VALUES(timestamp)
    """, data)

    connection.commit()
    cursor.close()
    connection.close()

@app.route('/run_monitor', methods=['POST'])
def run_monitor():
    """Runs improve_monitor.py manually from the dashboard"""
    try:
        subprocess.Popen(["python3", "improve_monitor.py"])
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error running monitoring script: {e}", 500

@app.route('/')
def index():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM website_metrics ORDER BY timestamp DESC LIMIT 50")
    metrics = cursor.fetchall()

    cursor.close()
    connection.close()
    
    return render_template('index.html', metrics=metrics)

@app.route('/metrics/<path:url>')
def metrics(url):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM website_metrics WHERE url = %s ORDER BY timestamp ASC", (url,))
    data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('metrics.html', url=url, data=data)

@app.route('/add_website', methods=['GET', 'POST'])
def add_website():
    if request.method == 'POST':
        url = request.form['url']
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_websites (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(255) UNIQUE,
                added_on DATETIME
            )
        """)
        
        cursor.execute("INSERT INTO monitored_websites (url, added_on) VALUES (%s, %s) ON DUPLICATE KEY UPDATE added_on = VALUES(added_on)", (url, datetime.now()))
        connection.commit()

        cursor.close()
        connection.close()

        run_curl_and_store(url)

        return redirect(url_for('index'))
    
    return render_template('add_website.html')

if __name__ == '__main__':
    app.run(debug=True)

