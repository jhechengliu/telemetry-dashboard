// Global state
let latestData = {};
let groups = {};

// DOM elements
const statusElement = document.getElementById('status');
const statsElement = document.getElementById('stats');
const groupsContainer = document.getElementById('groups-container');

// WebSocket connection
const socket = io();

// Initialize groups
function initializeGroups() {
    // Create 10 groups
    for (let i = 0; i < 10; i++) {
        const group = {
            id: i,
            voltages: Array(12).fill(null),
            temperatures: Array(5).fill(null)
        };
        groups[i] = group;
    }
}

// Update group data
function updateGroupData(signalName, value) {
    // Parse signal name: group-{id}-{voltage|temp}-{number}
    const match = signalName.match(/group-(\d+)-(voltage|temp)-(\d+)/);
    if (!match) {
        console.log('No match for signal:', signalName);  // Debug log
        return;
    }

    const [, groupId, type, index] = match;
    const group = groups[groupId];
    if (!group) {
        console.log('No group found for ID:', groupId);  // Debug log
        return;
    }

    const idx = parseInt(index) - 1;  // Convert to 0-based index
    if (type === 'voltage') {
        if (idx >= 0 && idx < 12) {
            group.voltages[idx] = value;
            console.log(`Updated voltage ${idx + 1} for group ${groupId}:`, value);  // Debug log
        }
    } else if (type === 'temp') {
        if (idx >= 0 && idx < 5) {
            group.temperatures[idx] = value;
            console.log(`Updated temperature ${idx + 1} for group ${groupId}:`, value);  // Debug log
        }
    }
}

// Render group data
function renderGroup(group) {
    const groupElement = document.getElementById(`group-${group.id}`);
    if (!groupElement) {
        console.log('No element found for group:', group.id);  // Debug log
        return;
    }

    // Update voltages
    group.voltages.forEach((voltage, index) => {
        const element = groupElement.querySelector(`.voltage-${index + 1}`);
        if (element && voltage !== null) {
            element.textContent = voltage.toFixed(2) + 'V';
        }
    });

    // Update temperatures
    group.temperatures.forEach((temp, index) => {
        const element = groupElement.querySelector(`.temp-${index + 1}`);
        if (element && temp !== null) {
            element.textContent = temp.toFixed(1) + '°C';
        }
    });
}

// WebSocket event handlers
socket.on('connect', () => {
    statusElement.textContent = 'Connected';
    statusElement.className = 'status connected';
});

socket.on('disconnect', () => {
    statusElement.textContent = 'Disconnected';
    statusElement.className = 'status disconnected';
});

socket.on('update', (data) => {
    console.log('Received update:', data);  // Debug log
    latestData[data.name] = data;

    // GPS: show latest received value for any group
    if (data.name.endsWith('-latitude')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('gps-latitude').textContent = data.value.toFixed(7);
    } else if (data.name.endsWith('-longitude')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('gps-longitude').textContent = data.value.toFixed(7);
    }
    // Motor: show latest received value for any group
    else if (data.name.endsWith('motor_rpm')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('motor-rpm').textContent = data.value.toFixed(0);
    } else if (data.name.endsWith('motor_temp')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('motor-temp').textContent = data.value.toFixed(1) + '°C';
    } else if (data.name.endsWith('motor_current')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('motor-current').textContent = data.value.toFixed(1) + 'A';
    } else if (data.name.endsWith('motor_torque')) {
        console.log('Updating DOM for:', data.name, 'with value:', data.value);
        document.getElementById('motor-torque').textContent = data.value.toFixed(1) + 'Nm';
    } else {
        updateGroupData(data.name, data.value);
        const groupId = data.name.split('-')[1];
        renderGroup(groups[groupId]);
    }
});

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        statsElement.innerHTML = `
            Uptime: ${Math.floor(data.uptime / 60)}m ${Math.floor(data.uptime % 60)}s<br>
            Packets: ${data.stats.packets_received}<br>
            Processed: ${data.stats.packets_processed}<br>
            Malformed: ${data.stats.packets_malformed}
        `;
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Initialize
initializeGroups();
setInterval(checkHealth, 1000);
checkHealth(); 