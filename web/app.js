import { animate } from './canvas.js';

const btn = document.getElementById('simulate-btn');
const resultsSection = document.getElementById('results');
const errorMsg = document.getElementById('error-msg');

async function loadSystems() {
    const res = await fetch('/api/systems');
    if (!res.ok) {
        showError('Failed to load systems from API');
        return;
    }
    const systems = await res.json();
    const select = document.getElementById('system-select');
    for (const s of systems) {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
    }
}

function readInputs() {
    return {
        system_id:       document.getElementById('system-select').value,
        n_threats:       parseInt(document.getElementById('n-threats').value, 10),
        inventory:       parseInt(document.getElementById('inventory').value, 10),
        launch_angle_deg: parseFloat(document.getElementById('launch-angle').value),
        zone_width:      parseFloat(document.getElementById('zone-width').value),
    };
}

async function runSimulation() {
    btn.disabled = true;
    try {
        clearError();
        const payload = readInputs();
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json();
            showError(err.detail || `Simulation failed (HTTP ${res.status})`);
            return;
        }
        const data = await res.json();
        animate(data);
        updateResults(data);
    } catch (e) {
        showError(`Network error: ${e.message}`);
    } finally {
        btn.disabled = false;
    }
}

function updateResults(response) {
    const s = response.report_summary;
    document.getElementById('r-neutralized').textContent = s.neutralized;
    document.getElementById('r-leaked').textContent      = s.leaked;
    document.getElementById('r-safe').textContent        = s.safe;
    document.getElementById('r-inventory').textContent   = response.inventory_remaining;
    document.getElementById('r-time').textContent        = response.final_time.toFixed(1);
    resultsSection.hidden = false;
}

function showError(message) {
    errorMsg.textContent = message;
    errorMsg.hidden = false;
    resultsSection.hidden = true;
}

function clearError() {
    errorMsg.hidden = true;
    errorMsg.textContent = '';
}

document.addEventListener('DOMContentLoaded', () => {
    loadSystems();
    btn.addEventListener('click', runSimulation);
});
