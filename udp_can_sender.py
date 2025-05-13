#!/usr/bin/env python3
import random
import socket
import struct
import time
import argparse
import logging
import json
import signal
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('udp-can-sender')

# Default configuration
DEFAULT_TARGET_IP = "127.0.0.1"
DEFAULT_TARGET_PORT = 1234
DEFAULT_RATE_HZ = 10

# CAN ID bases
CV1_BASE = 0x12905301  # Cell voltages 1-3
CV2_BASE = 0x12905381  # Cell voltages 4-6
CV3_BASE = 0x12905401  # Cell voltages 7-9
CV4_BASE = 0x12905481  # Cell voltages 10-12
CT1_BASE = 0x12905601  # Temperatures 1-3
CT2_BASE = 0x12905681  # Temperatures 4-5
GPS_CAN_ID = 0x18FEF3FE
MOTOR_CAN_ID = 0x0A7

class GroupState:
    def __init__(self, group_num):
        self.group_num = group_num
        # Initialize 12 battery voltages
        self.voltages = [random.uniform(3800, 4000) for _ in range(12)]
        # Initialize 5 temperatures
        self.temperatures = [random.uniform(25, 35) for _ in range(5)]
        # Trends for realistic simulation
        self.voltage_trends = [random.uniform(-1, 1) for _ in range(12)]
        self.temp_trends = [random.uniform(-0.5, 0.5) for _ in range(5)]

class SignalState:
    def __init__(self, board_ids):
        # Initialize specified groups
        self.groups = [GroupState(board_id) for board_id in board_ids]
        # Simulation parameters
        self.running = True
        self.packets_sent = 0
        self.time_elapsed = 0

class AppState:
    def __init__(self):
        self.running = True

app_state = AppState()

global_state = None  # Define at module level

# Build CAN frame in string format
def build_frame(can_id, raw_bytes):
    """Convert CAN ID and data bytes to a formatted string"""
    return f"{can_id:X}:{raw_bytes.hex().upper()}"

# Convert physical value to raw bytes
def phys_to_raw(value, scale=1, bytes_len=2):
    """Convert physical value to raw bytes with little endian encoding"""
    raw_int = int(value / scale)
    return raw_int.to_bytes(bytes_len, "little", signed=False)

# Handle graceful shutdown
def signal_handler(sig, frame):
    global global_state
    logger.info("Shutting down...")
    if global_state is not None:
        global_state.running = False
    sys.exit(0)

def simulate_step(state, time_delta):
    """Update all signal values to simulate real-world behavior"""
    for group in state.groups:
        # Update voltage trends randomly
        for i in range(12):
            if random.random() < 0.1:
                group.voltage_trends[i] = random.uniform(-1, 1)
            # Apply voltage changes
            group.voltages[i] += group.voltage_trends[i] * time_delta * 5
            # Keep within reasonable bounds
            group.voltages[i] = max(3700, min(4200, group.voltages[i]))

        # Update temperature trends randomly
        for i in range(5):
            if random.random() < 0.05:
                group.temp_trends[i] = random.uniform(-0.5, 0.5)
            # Apply temperature changes
            group.temperatures[i] += group.temp_trends[i] * time_delta
            # Keep within reasonable bounds
            group.temperatures[i] = max(20, min(60, group.temperatures[i]))

    return state

def simulate_gps():
    # Simulate a random walk around a fixed point
    base_lat = 25.033964
    base_lon = 121.564468
    lat = base_lat + random.uniform(-0.0005, 0.0005)
    lon = base_lon + random.uniform(-0.0005, 0.0005)
    lat_raw = int(lat * 1e7)
    lon_raw = int(lon * 1e7)
    data = struct.pack('<ii', lat_raw, lon_raw)
    return data

def simulate_motor():
    # Simulate current and torque
    current = random.uniform(-100, 100)  # A
    torque = random.uniform(-300, 300)   # Nm
    current_raw = int(current * 10)
    torque_raw = int(torque * 10)
    data = struct.pack('<hh', current_raw, torque_raw)
    return data

def run_simulation(target_ip, target_port, rate_hz, board_ids):
    """Run the UDP CAN sender simulation"""
    global global_state
    global_state = SignalState(board_ids)
    state = global_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / rate_hz
    
    logger.info(f"Starting CAN UDP sender - targeting {target_ip}:{target_port} at {rate_hz}Hz")
    logger.info(f"Simulating boards: {board_ids}")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    last_stats_time = time.time()
    start_time = time.time()
    
    try:
        while state.running:
            cycle_start = time.time()
            
            # Calculate how much time has passed since last cycle
            time_delta = interval
            
            # Update simulation state
            state = simulate_step(state, time_delta)
            
            # Create and send CAN frames for each group
            try:
                for group in state.groups:
                    # Send cell voltages (4 frames per group)
                    # CV1: Cells 1-3
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(v, 1) for v in group.voltages[0:3])
                    frame = build_frame(CV1_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1

                    # CV2: Cells 4-6
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(v, 1) for v in group.voltages[3:6])
                    frame = build_frame(CV2_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1

                    # CV3: Cells 7-9
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(v, 1) for v in group.voltages[6:9])
                    frame = build_frame(CV3_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1

                    # CV4: Cells 10-12
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(v, 1) for v in group.voltages[9:12])
                    frame = build_frame(CV4_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1

                    # Send temperatures (2 frames per group)
                    # CT1: Temperatures 1-3
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(t, 0.1) for t in group.temperatures[0:3])
                    frame = build_frame(CT1_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1

                    # CT2: Temperatures 4-5
                    data = bytes([group.group_num]) + b''.join(phys_to_raw(t, 0.1) for t in group.temperatures[3:5])
                    frame = build_frame(CT2_BASE, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
                    state.packets_sent += 1
                
                # Send GPS frame
                gps_data = simulate_gps()
                gps_frame = build_frame(GPS_CAN_ID, gps_data)
                sock.sendto(gps_frame.encode(), (target_ip, target_port))
                state.packets_sent += 1

                # Send Motor frame
                motor_data = simulate_motor()
                motor_frame = build_frame(MOTOR_CAN_ID, motor_data)
                sock.sendto(motor_frame.encode(), (target_ip, target_port))
                state.packets_sent += 1
                
                # Update statistics
                state.time_elapsed = time.time() - start_time
                
            except socket.error as e:
                logger.error(f"Socket error: {e}")
            
            # Log stats periodically
            if time.time() - last_stats_time > 5:
                logger.info(f"Sent {state.packets_sent} packets in {state.time_elapsed:.1f}s "
                            f"({state.packets_sent / state.time_elapsed:.1f} packets/s)")
                last_stats_time = time.time()
            
            # Sleep to maintain the desired rate
            elapsed = time.time() - cycle_start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
    
    finally:
        sock.close()
        logger.info("Simulation ended")
        print("Simulation ended. Goodbye!")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='UDP CAN Frame Sender')
    parser.add_argument('--ip', type=str, default=DEFAULT_TARGET_IP,
                        help=f'Target IP address (default: {DEFAULT_TARGET_IP})')
    parser.add_argument('--port', type=int, default=DEFAULT_TARGET_PORT,
                        help=f'Target UDP port (default: {DEFAULT_TARGET_PORT})')
    parser.add_argument('--rate', type=float, default=DEFAULT_RATE_HZ,
                        help=f'Send rate in Hz (default: {DEFAULT_RATE_HZ})')
    parser.add_argument('--boards', type=str, default='0,1,2,3,4,5,6,7,8,9',
                        help='Comma-separated list of board IDs to simulate (default: 0,1,2,3,4,5,6,7,8,9)')
    
    args = parser.parse_args()
    board_ids = [int(x) for x in args.boards.split(',')]
    run_simulation(args.ip, args.port, args.rate, board_ids)
