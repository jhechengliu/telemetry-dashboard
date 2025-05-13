# Battery Telemetry Dashboard — Real-Time CAN Data Display

## Overview

This project provides a real-time web-based dashboard for monitoring battery pack data sent over UDP. The system uses Flask and Flask-SocketIO to receive, decode, and display values live in a browser. It supports monitoring of 10 battery groups, each containing 12 voltage readings and 5 temperature sensors, with collapsible UI sections for better organization.

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
[UDP Listener Thread] ──> [Flask + SocketIO] ──> [Browser Dashboard]
```

- UDP packets contain CAN messages with battery data
- Flask runs a background thread to listen for UDP packets
- Parsed values are forwarded to the frontend using WebSockets (Socket.IO)
- The dashboard updates UI elements instantly when new values arrive
- Data is organized into collapsible battery groups

---

## 2. Key Features

- **Battery Group Monitoring**: 10 groups with 12 voltages and 5 temperatures each
- **Collapsible UI**: Expand/collapse battery groups for better organization
- **Live updates** via WebSocket (no polling)
- **Flexible CAN signal parsing** through a `can_map.json` file
- **Easy to test** with built-in UDP simulator
- **Minimal dependencies**: Flask, Flask-SocketIO, Eventlet
- Mobile-friendly and responsive design

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
    ├── css/
    │   └── style.css      # CSS styling for the dashboard
    └── js/
        └── main.js        # Frontend JavaScript code
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
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages
pip install flask flask-socketio eventlet
```

---

## 5. Running the System

### Start the Flask server
```bash
python3 app.py
```

### Access the dashboard
Open your browser to:
```
http://localhost:5001
```

You will see a dashboard with:
- 10 collapsible battery groups
- 12 voltage readings per group
- 5 temperature readings per group
- Connection status and statistics

### (Optional) Simulate data for testing
```bash
python3 udp_can_sender.py
```

---

## 6. CAN Signal Mapping (`can_map.json`)

The `can_map.json` file defines the CAN message structure for battery data. Example:

```json
{
  "0x12905301": {
    "name": "CV1",
    "description": "Cell Voltages 1-3",
    "signals": [
      {
        "name": "pack_id",
        "start": 0,
        "length": 1
      },
      {
        "name": "cell_1",
        "start": 2,
        "length": 2,
        "unit": "mV"
      }
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

The script `udp_can_sender.py` simulates battery data for testing:
- Generates realistic voltage and temperature values
- Simulates 10 battery groups
- Sends data at configurable rate
- Supports command-line configuration

Usage:
```bash
python3 udp_can_sender.py [--ip IP] [--port PORT] [--rate RATE] [--boards BOARD_IDS]
```

---

## 8. Extending the Dashboard

### Add a new signal:
1. Edit `can_map.json` to add new CAN IDs and signals
2. Update the frontend JavaScript in `static/js/main.js`
3. Add corresponding UI elements in `templates/index.html`
4. Restart the server:
```bash
python3 app.py
```

---

## 9. Troubleshooting

| Issue                            | Fix                                                  |
|----------------------------------|-------------------------------------------------------|
| Port 1234 already in use         | Change UDP port in `app.py`                          |
| No data appearing on dashboard   | Check if `udp_can_sender.py` is running              |
| WebSocket not updating UI        | Open browser console (F12) and check for JS errors   |
| "ModuleNotFoundError" on launch  | Activate virtual environment & install dependencies  |

---

## Credits & Contact

Developed by: [Your Name / Team Name]  
For: [University / Student Racing Team Name]  
Contact: [your.email@example.com]
