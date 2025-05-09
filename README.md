
# Telemetry Dashboard — Real-Time CAN Data Display

## Overview

This project provides a real-time web-based dashboard for monitoring CAN bus data sent from an ESP32 over UDP. The system uses Flask and Flask-SocketIO to receive, decode, and display values live in a browser. It supports flexible signal mapping via a JSON configuration and can simulate CAN data for testing purposes.

---

## Table of Contents

1. [System Architecture](#system-architecture)  
2. [Key Features](#key-features)  
3. [Project Structure](#project-structure)  
4. [Setup Instructions](#setup-instructions)  
5. [Running the System](#running-the-system)  
6. [CAN Signal Mapping (`can_map.json`)](#can-signal-mapping-can_mapjson)  
7. [Virtual CAN Sender](#virtual-can-sender)  
8. [Extending the Dashboard](#extending-the-dashboard)  
9. [Troubleshooting](#troubleshooting)  

---

## 1. System Architecture

```
ESP32 (CAN → UDP) ──> [UDP Listener Thread] ──> [Flask + SocketIO] ──> [Browser Dashboard]
```

- ESP32 reads CAN messages and transmits over UDP.
- Flask runs a background thread to listen for UDP packets.
- Parsed values are forwarded to the frontend using WebSockets (Socket.IO).
- The dashboard updates UI elements instantly when new values arrive.

---

## 2. Key Features

- **Live updates** via WebSocket (no polling).
- **Flexible CAN signal parsing** through a `can_map.json` file.
- **Easy to test** with built-in UDP simulator.
- **Minimal dependencies**: Flask, Flask-SocketIO, Eventlet.
- Mobile-friendly and lightweight frontend.

---

## 3. Project Structure

```
telemetry-dashboard/
│
├── app.py                 # Main Flask + UDP + WebSocket app
├── can_map.json           # CAN ID and signal mapping configuration
├── udp_can_sender.py      # Simulates virtual CAN messages over UDP
│
├── templates/
│   └── index.html         # The main dashboard UI
│
└── static/
    └── style.css          # CSS styling for the dashboard
```

---

## 4. Setup Instructions

### Requirements
- Python 3.7+
- pip

### Installation Steps

```bash
# Clone or unzip the project folder
cd telemetry-dashboard

# (Optional) Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install flask flask-socketio eventlet
```

---

## 5. Running the System

### Start the Flask server
```bash
python app.py
```

### Access the dashboard
Open your browser to:
```
http://localhost:5000
```

You will see a simple dashboard with real-time fields such as:
- Highest Temp.
- Lowest Temp.
- Highest/Lowest/Average Cell Voltage
- TS Voltage

### (Optional) Simulate data for testing
```bash
python udp_can_sender.py
```

---

## 6. CAN Signal Mapping (`can_map.json`)

The `can_map.json` file allows flexible mapping of CAN IDs and data layouts. Example:

```json
{
  "0x100": {
    "signals": [
      { "name": "highest_temp", "start": 0, "length": 2, "scale": 0.1, "unit": "°C" },
      { "name": "lowest_temp",  "start": 2, "length": 2, "scale": 0.1, "unit": "°C" }
    ]
  }
}
```

### Field Explanation:
| Key       | Description                              |
|-----------|------------------------------------------|
| `name`    | Signal name (used in HTML element ID)    |
| `start`   | Byte offset in CAN data payload          |
| `length`  | Number of bytes for this signal          |
| `scale`   | Multiplier applied to raw value          |
| `unit`    | Display unit shown in the dashboard      |

**Note**: All values are assumed to be unsigned integers in **little-endian** byte order.

---

## 7. Virtual CAN Sender

The script `udp_can_sender.py` randomly generates data and sends UDP packets formatted like:
```
100:0A1B2C...
```

This mimics real CAN frames from the ESP32 and is useful for offline testing.

---

## 8. Extending the Dashboard

### Add a new signal:
1. Edit `can_map.json`:
```json
"0x105": {
  "signals": [
    { "name": "battery_soc", "start": 0, "length": 1, "scale": 1, "unit": "%" }
  ]
}
```

2. Add a new div to `index.html`:
```html
<div class="label">Battery SoC</div>
<div id="battery_soc" class="value">---</div>
```

3. Restart the server:
```bash
python app.py
```

---

## 9. Troubleshooting

| Issue                            | Fix                                                  |
|----------------------------------|-------------------------------------------------------|
| Port 1234 already in use         | Change UDP port in `app.py`                          |
| No data appearing on dashboard   | Check if ESP32 or `udp_can_sender.py` is sending     |
| WebSocket not updating UI        | Open browser console (F12) and check for JS errors   |
| “ModuleNotFoundError” on launch  | Activate virtual environment & install dependencies  |

---

## Credits & Contact

Developed by: [Your Name / Team Name]  
For: [University / Student Racing Team Name]  
Contact: [your.email@example.com]
