import time
import mysql.connector
from improve_monitor import run_curl_command, store_data

# Database configuration
db_config = {
    'user': 'monitor_user',
    'password': 'monitor',
    'host': 'localhost',
    'database': 'website_monitor'
}

def fetch_websites():
    """Fetch all monitored websites from the database."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    cursor.execute("SELECT url FROM monitored_websites")
    websites = [row[0] for row in cursor.fetchall()]

    cursor.close()
    connection.close()
    return websites

def periodic_monitor(interval):
    """Runs website monitoring every X seconds."""
    while True:
        websites = fetch_websites()
        for site in websites:
            metrics = run_curl_command(site)
            store_data(db_config, site, metrics)
            print(f"Updated metrics for {site}")

        print("Monitoring cycle completed. Sleeping...")
        time.sleep(interval)

# Run monitoring every 5 minutes (300 seconds)
if __name__ == "__main__":
    periodic_monitor(30)

