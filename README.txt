# Website Monitoring Application

## Project Overview

This project is a web application designed to monitor website performance and availability. It uses `curl` to gather various metrics such as response times, download/upload speeds, and connection times. Additionally, it utilizes `tcpdump` to capture network traffic and identify issues like duplicate ACKs. The application features a Flask-based web interface for displaying metrics, adding new websites to monitor, and manually triggering monitoring tasks. A scheduler component allows for periodic, automated monitoring of the configured websites. Data is stored in a MySQL database.

## File Structure

website_monitor/
│   ├── flask_monitor_app.py     # Flask web interface and API
│   ├── improve_monitor.py       # Script for on-demand detailed monitoring with tcpdump
│   ├── scheduler_monitor.py     # Script for periodic, scheduled monitoring
│   ├── db_setup.py              # Script to initialize the database schema
│   ├── Requirements.txt         # Required Python packages
│   └── README.md                # This README file
├── templates/                   # HTML Templates for Flask
│   ├── index.html               # Main dashboard to display metrics
│   ├── add_website.html         # Form to add new websites for monitoring
│   └── metrics.html             # Page to display historical metrics and graphs for a specific website

## Prerequisites

Before you begin, ensure you have the following installed:
* Python 3.x
* MySQL Server
* `curl` command-line tool
* `tcpdump` command-line tool
* `pip` for installing Python packages

## Setup and Installation

1.  **Clone the Repository (if applicable)**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-directory>
    ```

2.  **Create and Activate a Python Virtual Environment (Recommended)**
    ```bash
    python3 -m venv monitor_env
    source monitor_env/bin/activate  # On Windows use: monitor_env\Scripts\activate
    ```

3.  **Install Required Python Packages** [cite: 1]
    ```bash
    pip install -r Requirements.txt
    ```

4.  **Database Configuration**
    * Ensure your MySQL server is running.
    * Create a database user and database for the application. The default credentials used in the scripts are:
        * User: `monitor_user`
        * Password: `monitor`
        * Database: `website_monitor`
        * Host: `localhost`
    * You can create the user and grant privileges using commands like:
        ```sql
        CREATE USER 'monitor_user'@'localhost' IDENTIFIED BY 'monitor';
        CREATE DATABASE website_monitor;
        GRANT ALL PRIVILEGES ON website_monitor.* TO 'monitor_user'@'localhost';
        FLUSH PRIVILEGES;
        ```
    * Modify the `db_config` dictionary in `flask_monitor_app.py`, `scheduler_monitor.py`, `db_setup.py`, and `improve_monitor.py` if your MySQL setup differs.

5.  **Initialize Database Schema**
    Run the `db_setup.py` script to create the necessary tables:
    ```bash
    python db_setup.py
    ```
    This will create two tables: `monitored_websites` and `website_metrics`. [cite: 4]

6.  **Configure Network Interface for `improve_monitor.py`**
    * **VERY IMPORTANT:** Open `improve_monitor.py` and find the `NETWORK_INTERFACE` variable.
    * You **MUST** change the placeholder value (e.g., `'enp0s3'`) to your actual active network interface name.
        * On Linux/macOS, you can find this using commands like `ip addr` or `ifconfig`.
        * On Windows, you might need to find the interface name through Network Connections or use `getmac` or `ipconfig` and adapt the `tcpdump` command if using a Windows port of `tcpdump` (like WinDump).
    * The script `improve_monitor.py` also uses a random port range (`PORT_RANGE_START` and `PORT_RANGE_END`) for `curl` and a PCAP file template (`PCAP_FILE_TEMPLATE`). You can adjust these if needed.

## Running the Application

You will typically need to run three main components, potentially in separate terminal windows/sessions (after activating the virtual environment in each).

1.  **Flask Web Application (`flask_monitor_app.py`)**
    This application provides the web interface to view data and add websites.
    ```bash
    python flask_monitor_app.py
    ```
    By default, it will be accessible at `http://127.0.0.1:5000`.

2.  **Scheduled Monitoring (`scheduler_monitor.py`)**
    This script runs in the background to periodically check the websites listed in the database.
    ```bash
    python scheduler_monitor.py
    ```
    By default, it checks websites every 30 seconds (this interval is configurable in the script).

3.  **On-Demand Detailed Monitoring (`improve_monitor.py`)**
    This script can be run manually to perform a detailed check on websites, including `tcpdump` analysis for duplicate ACKs. The Flask application also provides a button to trigger this script.
    ```bash
    python improve_monitor.py
    ```
    This script will check websites defined in `HARDCODED_WEBSITES` and any websites fetched from the `monitored_websites` table.

## Using the Web Interface

* **Dashboard (`/` or `http://127.0.0.1:5000`):** Displays the latest metrics for all monitored websites. [cite: 2]
* **Add New Website (`/add_website`):** Allows you to add new URLs to the monitoring list. [cite: 3]
* **Run Monitoring Button:** Manually triggers the `improve_monitor.py` script.
* **Metrics per URL (click on a URL in the dashboard):** Shows historical data and charts for response time and download speed for a specific website.

## Database Interaction [cite: 4]

You can interact with the database directly using a MySQL client.

* **Login to Database:**
    ```bash
    mysql -u monitor_user -p -D website_monitor
    ```
    Enter the password (`monitor` by default) when prompted.

* **Useful MySQL Commands:**
    ```sql
    SHOW TABLES;
    DESCRIBE website_metrics;
    DESCRIBE monitored_websites;
    SELECT * FROM monitored_websites;
    SELECT * FROM website_metrics WHERE url = '[https://example.com](https://example.com)' ORDER BY timestamp DESC;
    -- To clear all metrics data (use with caution):
    TRUNCATE TABLE website_metrics;
    ```
* **Database File Location (Example for some Linux systems):** [cite: 5]
    ```bash
    sudo ls /var/lib/mysql/website_monitor/
    ```

## Notes

* Ensure that the user running the scripts (especially `improve_monitor.py` for `tcpdump`) has the necessary permissions to capture network traffic on the specified interface. This might require running the script with `sudo` or adjusting user permissions/capabilities for `tcpdump`.
* The `improve_monitor.py` script generates temporary `.pcap` files during its operation and attempts to delete them afterward. Ensure the script has write/delete permissions in its working directory.
* The hardcoded websites in `improve_monitor.py` (`https://delfi.lt`, `https://google.com`) will always be checked by that script, in addition to those from the database.