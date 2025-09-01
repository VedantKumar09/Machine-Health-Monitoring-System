# IoT-Based Machine Health Monitoring System

This project is an end-to-end solution for monitoring machine health using IoT sensors, a machine learning backend, and a web-based dashboard. It collects real-time data, predicts potential failures, and visualizes the machine's status.

## Key Features

*   **Real-time Data Collection**: An ESP32-based sensor node (`Node.ino`) captures temperature, humidity, and sound levels.
*   **Wireless Communication**: Sensor data is transmitted from the node to a central hub (`Hub.ino`) using the ESP-NOW protocol.
*   **Cloud Integration**: The hub uploads sensor readings to Google Sheets, creating a centralized data log.
*   **Predictive Maintenance**: A Flask backend (`app.py`) processes the data and uses a pre-trained machine learning model to predict the machine's health status.
*   **Interactive Dashboard**: A dynamic web dashboard (`templates/index.html`) built with Chart.js visualizes historical data, aggregated analysis, and health predictions.
*   **Flexible Analysis**: View machine performance data aggregated over different timeframes (hourly, weekly, monthly, and yearly).

## How It Works

1.  The **Sensor Node** reads data from its sensors.
2.  It sends the data wirelessly to the **Hub** via ESP-NOW.
3.  The **Hub** receives the data, performs a basic health assessment, and uploads the record to a Google Sheet.
4.  The **Flask Backend** fetches data from the Google Sheet or a local CSV file (`sample_data.csv`).
5.  The backend aggregates the data and uses a machine learning model to predict the machine's health status.
6.  The **Web Dashboard** calls API endpoints on the Flask server to retrieve and display the data in charts and tables for analysis.

## Project Components

*   **Hardware (Arduino/ESP32)**
    *   **Sensors**:
        *   `DHT11`: For temperature and humidity readings.
        *   `KY-037`: For sound level detection.
    *   [`Node.ino`](Node.ino): Firmware for the sensor data collection node, reading data from the DHT11 and KY-037 sensors.
    *   [`Hub.ino`](Hub.ino): Firmware for the hub that aggregates data and communicates with the cloud.
*   **Backend (Python/Flask)**
    *   [`app.py`](app.py): The web server that handles API requests, data processing, and machine learning predictions.
*   **Frontend (HTML/CSS/JS)**
    *   [`templates/index.html`](templates/index.html): The main dashboard for data visualization.
    *   [`templates/style.css`](templates/style.css): Custom styles for the dashboard.
