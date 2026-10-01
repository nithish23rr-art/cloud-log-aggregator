// Theme toggler
function changeThemeVariant(theme) { 
    document.getElementById('htmlRoot').setAttribute('data-bs-theme', theme); 
}

function runChaosMonkey() { 
    alert("M&K Chaos Monkey Validator injected test fault: Mesh recovered successfully."); 
}

function openVisualRegexBuilder() { 
    alert("M&K Visual Regex Builder opened."); 
}

function exportLogsCSV() { 
    alert("Audit CSV exported successfully!"); 
}

function triggerVoiceAssistant() {
    alert("Voice AI Assistant activated listening mode...");
}

function filterLogs() {
    let input = document.getElementById('searchInput').value.toLowerCase();
    let rows = document.querySelectorAll('#logList tr');
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(input) ? '' : 'none';
    });
}

// Socket.IO Real-time Integration
const socket = io();

socket.on('connect', () => {
    console.log("Connected to M&K Nexus WebSocket Gateway.");
});

// Listen for incoming live logs
socket.on('new_log', (data) => {
    const tbody = document.getElementById('logList');
    const newRow = document.createElement('tr');
    newRow.className = 'log-row';
    
    let badgeColor = data.level === 'ERROR' ? 'danger' : (data.level === 'WARNING' ? 'warning' : 'info');

    newRow.innerHTML = `
        <td><i class="bi bi-star"></i></td>
        <td class="text-muted small">[${data.timestamp}]</td>
        <td class="text-muted small font-monospace">${data.trace_id}</td>
        <td><span class="badge bg-${badgeColor}">${data.level}</span></td>
        <td><span class="badge bg-secondary">${data.tag}</span></td>
        <td><span class="badge bg-success">Neutral</span></td>
        <td class="fw-medium log-message">${data.message}</td>
    `;
    tbody.insertBefore(newRow, tbody.firstChild);
});

// Terminal Shell Input Handler
const terminalInput = document.getElementById('terminalInput');
const terminalOutput = document.getElementById('terminalOutput');

if (terminalInput) {
    terminalInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            let command = terminalInput.value;
            terminalInput.value = '';
            socket.emit('terminal_command', { command: command });
        }
    });
}

// Listen for terminal output from backend
socket.on('terminal_response', (data) => {
    if (terminalOutput) {
        if (data.output.includes('CLEAR')) {
            terminalOutput.innerHTML = "M&K Nexus Cloud Enterprise Terminal v15.0 Active...\n";
        } else {
            terminalOutput.innerHTML += "\n" + data.output;
        }
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
});