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

# Signal states and parameters
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
    def __init__(self):
        # Initialize 10 groups
        self.groups = [GroupState(i+1) for i in range(10)]
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

def run_simulation(target_ip, target_port, rate_hz):
    """Run the UDP CAN sender simulation"""
    global global_state
    global_state = SignalState()
    state = global_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / rate_hz
    
    logger.info(f"Starting CAN UDP sender - targeting {target_ip}:{target_port} at {rate_hz}Hz")
    
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
                    # Send voltages (3 frames per group, 4 voltages per frame)
                    for i in range(0, 12, 4):
                        can_id = 0x100 + (group.group_num * 10) + (i // 4)
                        data = b''
                        for j in range(4):
                            if i + j < 12:
                                data += phys_to_raw(group.voltages[i + j], 1)
                            else:
                                data += b'\x00\x00'
                        frame = build_frame(can_id, data)
                        sock.sendto(frame.encode(), (target_ip, target_port))
                        state.packets_sent += 1

                    # Send temperatures (1 frame per group, all 5 temperatures)
                    can_id = 0x100 + (group.group_num * 10) + 3
                    data = b''
                    for temp in group.temperatures:
                        data += phys_to_raw(temp, 0.1)
                    frame = build_frame(can_id, data)
                    sock.sendto(frame.encode(), (target_ip, target_port))
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
    
    args = parser.parse_args()
    run_simulation(args.ip, args.port, args.rate)
