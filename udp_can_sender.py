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
class SignalState:
    def __init__(self):
        # Temperature parameters
        self.temp_trend = 0  # Direction of temperature change
        self.hi_temp = 40.0  # Starting temperature
        self.lo_temp = 30.0  # Starting temperature
        
        # Voltage parameters
        self.voltage_trend = 0  # Direction of voltage change
        self.hi_cell_mv = 4050  # Starting cell voltage
        self.lo_cell_mv = 3950  # Starting cell voltage
        
        # System voltage
        self.ts_voltage = 290.0  # Starting system voltage
        
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
    # Update temperature trends
    if random.random() < 0.05:
        state.temp_trend = random.uniform(-1, 1)
    
    # Apply temperature changes
    state.hi_temp += state.temp_trend * time_delta * 2
    state.lo_temp += state.temp_trend * time_delta
    
    # Keep temperatures within reasonable bounds
    state.hi_temp = max(30, min(60, state.hi_temp))
    state.lo_temp = max(20, min(45, state.lo_temp))
    
    # Ensure highest temp is actually higher than lowest
    if state.hi_temp < state.lo_temp + 5:
        state.hi_temp = state.lo_temp + 5
    
    # Update voltage trends
    if random.random() < 0.1:
        state.voltage_trend = random.uniform(-1, 1)
    
    # Apply voltage changes
    voltage_delta = state.voltage_trend * time_delta * 10
    state.hi_cell_mv += voltage_delta
    state.lo_cell_mv += voltage_delta
    
    # Keep voltages within reasonable bounds
    state.hi_cell_mv = max(3900, min(4200, state.hi_cell_mv))
    state.lo_cell_mv = max(3700, min(4100, state.lo_cell_mv))
    
    # Ensure highest voltage is actually higher than lowest
    if state.hi_cell_mv < state.lo_cell_mv + 50:
        state.hi_cell_mv = state.lo_cell_mv + 50
    
    # Simulate system voltage
    state.ts_voltage += random.uniform(-0.5, 0.5)
    state.ts_voltage = max(280, min(300, state.ts_voltage))
    
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
            
            # Create and send CAN frames
            try:
                # Temperature frame (ID 0x100)
                data_100 = phys_to_raw(state.hi_temp, 0.1) + phys_to_raw(state.lo_temp, 0.1)
                frame_100 = build_frame(0x100, data_100)
                sock.sendto(frame_100.encode(), (target_ip, target_port))
                
                # Cell voltage frame (ID 0x101)
                avg_mv = (state.hi_cell_mv + state.lo_cell_mv) // 2
                data_101 = phys_to_raw(state.hi_cell_mv, 1) + phys_to_raw(state.lo_cell_mv, 1) + phys_to_raw(avg_mv, 1)
                frame_101 = build_frame(0x101, data_101)
                sock.sendto(frame_101.encode(), (target_ip, target_port))
                
                # System voltage frame (ID 0x102)
                data_102 = phys_to_raw(state.ts_voltage, 0.01)
                frame_102 = build_frame(0x102, data_102)
                sock.sendto(frame_102.encode(), (target_ip, target_port))
                
                # Update statistics
                state.packets_sent += 3
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
