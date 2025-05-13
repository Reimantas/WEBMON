import mysql.connector

db_config = {
    'user': 'monitor_user',
    'password': 'monitor',
    'host': 'localhost',
    'database': 'website_monitor'
}

connection = mysql.connector.connect(**db_config)
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS monitored_websites (
        id INT AUTO_INCREMENT PRIMARY KEY,
        url VARCHAR(255) UNIQUE,
        added_on DATETIME
    )
""")

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
duplicate_acks INT DEFAULT 0,  # <-- PRIDĖTA EILUTĖ
        timestamp DATETIME
    )
""")

connection.commit()
cursor.close()
connection.close()

print("Database setup complete!")
