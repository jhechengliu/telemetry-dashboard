import json
import re
import socket
import struct
import threading
import time
import logging
import signal
import sys
from pathlib import Path
from queue import Queue, Empty
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('telemetry-dashboard')

# Configuration constants
UDP_PORT = 1234
BUFFER_SZ = 1024
CAN_REGEX = re.compile(r'([0-9A-Fa-f]{1,8})[:# ]([0-9A-Fa-f]+)')
MAP_FILE = Path(__file__).with_name('can_map.json')
WEB_PORT = 5001

class AppState:
    def __init__(self):
        self.running = True

app_state = AppState()

def load_can_map():
    """Load and parse the CAN signal mapping configuration"""
    try:
        with MAP_FILE.open() as f:
            # Convert CAN IDs from hex strings to integers
            return {int(k, 16): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        logger.error(f"CAN map file not found: {MAP_FILE}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in CAN map file: {MAP_FILE}")
        return {}

# Load CAN signal mapping
can_map = load_can_map()

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'telemetry-dashboard-secret'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

# Data storage
latest_values = {}  # Store the latest values for each signal
update_queue = Queue()  # Queue for passing data between threads
stats = {
    'packets_received': 0,
    'packets_processed': 0,
    'packets_malformed': 0,
    'start_time': time.time()
}

def signal_handler(sig, frame):
    logger.info("Shutdown signal received, stopping all threads...")
    app_state.running = False
    time.sleep(1)  # Give threads time to exit
    logger.info("Shutdown complete")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def udp_receiver():
    """Background thread that listens for UDP packets containing CAN data"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)  # Add timeout for socket operations
    
    try:
        sock.bind(('0.0.0.0', UDP_PORT))
        logger.info(f"UDP listener started on 0.0.0.0:{UDP_PORT}")
        
        while app_state.running:
            try:
                raw, addr = sock.recvfrom(BUFFER_SZ)
                stats['packets_received'] += 1
                
                # Try to decode the received packet
                message = raw.decode().strip()
                m = CAN_REGEX.search(message)
                
                if not m:
                    stats['packets_malformed'] += 1
                    continue
                    
                can_id = int(m.group(1), 16)
                data = bytes.fromhex(m.group(2))
                process_can(can_id, data)
                
            except socket.timeout:
                continue
            except UnicodeDecodeError:
                stats['packets_malformed'] += 1
                logger.warning(f"Failed to decode UDP packet: {raw!r}")
            except Exception as e:
                stats['packets_malformed'] += 1
                logger.error(f"Error in UDP listener: {e}")
    
    except OSError as e:
        logger.critical(f"Failed to bind UDP socket: {e}")
        # Retry after a delay
        time.sleep(5)
        udp_receiver()  # Recursive restart of the function
    
    finally:
        sock.close()

def process_can(can_id: int, data: bytes):
    """Process a CAN message and extract signal values based on the mapping"""
    if can_id not in can_map:
        return
    
    try:
        mapping = can_map[can_id]['signals']
        pack_id = data[0]  # First byte is always pack_id
        
        for sig in mapping:
            if sig['name'] == 'pack_id':
                continue  # Skip pack_id as we already have it
                
            name = sig['name']
            start, length = sig['start'], sig['length']
            
            # Check if we have enough data
            if start + length > len(data):
                logger.warning(f"Signal {name} requires more data than available")
                continue
                
            # Extract and convert the raw value
            raw_val = int.from_bytes(data[start:start+length], 'little', signed=False)
            scale = sig.get('scale', 1)
            phys = raw_val * scale
            
            # Convert signal name to frontend format with dash
            if name.startswith('cell_'):
                num = name.split('_')[1]
                frontend_name = f"voltage-{num}"
            elif name.startswith('temp_'):
                num = name.split('_')[1]
                frontend_name = f"temp-{num}"
            else:
                frontend_name = name
            
            # Create signal name with group number
            group_signal_name = f"group-{pack_id}-{frontend_name}"
            
            # Create payload for the frontend
            payload = {
                "name": group_signal_name,
                "value": phys,
                "unit": sig.get('unit', ''),
                "timestamp": time.time()
            }
            
            update_queue.put(payload)
            logger.debug(f"Processed signal: {group_signal_name} = {phys} {sig.get('unit', '')}")
        
        stats['packets_processed'] += 1
    
    except Exception as e:
        logger.error(f"Error processing CAN ID 0x{can_id:X}: {e}")

def socketio_forwarder():
    """Forward data from the queue to connected WebSocket clients"""
    while app_state.running:
        try:
            # Get message from queue with timeout
            payload = update_queue.get(timeout=0.5)
            
            # Store the latest value
            latest_values[payload['name']] = payload
            
            # Send to all connected clients
            socketio.emit("update", payload)
            #logger.info(f"Emitted update: {payload['name']} = {payload['value']}")
            
        except Empty:
            # No data in queue, just continue
            socketio.sleep(0.01)
        except Exception as e:
            logger.error(f"Error in socketio forwarder: {e}")
            socketio.sleep(1)  # Delay on error

@app.route("/")
def index():
    """Render the dashboard HTML page"""
    return render_template("index.html")

@app.route("/health")
def health():
    """Health check endpoint with stats"""
    uptime = time.time() - stats['start_time']
    return jsonify({
        "status": "ok",
        "uptime": uptime,
        "stats": stats,
        "signals_count": len(latest_values)
    })

@app.route("/data")
def data():
    """API endpoint to get all latest values"""
    return jsonify(latest_values)

@socketio.event
def connect():
    """Handle new WebSocket client connections"""
    logger.info("Client connected")
    # Send all current values to the new client
    for payload in latest_values.values():
        emit("update", payload)

@socketio.event
def disconnect():
    """Handle WebSocket client disconnections"""
    logger.info("Client disconnected")

def monitor_thread():
    """Thread to periodically log system status"""
    while app_state.running:
        try:
            uptime = time.time() - stats['start_time']
            logger.info(f"Status: Uptime={uptime:.1f}s, "
                        f"Received={stats['packets_received']}, "
                        f"Processed={stats['packets_processed']}, "
                        f"Malformed={stats['packets_malformed']}")
            time.sleep(60)  # Log every minute
        except Exception as e:
            logger.error(f"Error in monitor thread: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Start background threads
    threading.Thread(target=udp_receiver, daemon=True).start()
    threading.Thread(target=socketio_forwarder, daemon=True).start()
    threading.Thread(target=monitor_thread, daemon=True).start()
    
    # Start the Flask server
    logger.info(f"Starting web server → http://localhost:{WEB_PORT}")
    socketio.run(app, host="0.0.0.0", port=WEB_PORT, debug=False)
