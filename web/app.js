import { animate } from './canvas.js';
import { patriotIcon, davidsSlingIcon, irisTIcon } from './assets/icons.js';

const btn = document.getElementById('simulate-btn');
const resultsSection = document.getElementById('results');
const errorMsg = document.getElementById('error-msg');

const SYSTEM_ICONS = {
    patriot:      patriotIcon,
    davids_sling: davidsSlingIcon,
    iris_t:       irisTIcon,
};

// ── Slider live value display ─────────────────────────────────────────

function fillPct(input) {
    return ((input.value - input.min) / (input.max - input.min) * 100).toFixed(1) + '%';
}

function setupSliders() {
    const sliders = [
        { id: 'n-threats',    valId: 'n-threats-val',    fmt: v => v },
        { id: 'inventory',    valId: 'inventory-val',    fmt: v => v },
        { id: 'launch-angle', valId: 'launch-angle-val', fmt: v => `${v}°` },
        { id: 'zone-width',   valId: 'zone-width-val',   fmt: v => `${v} m` },
    ];
    for (const { id, valId, fmt } of sliders) {
        const input = document.getElementById(id);
        const display = document.getElementById(valId);
        const update = () => {
            display.textContent = fmt(input.value);
            input.style.setProperty('--fill', fillPct(input));
        };
        input.addEventListener('input', update);
        update();
    }
}

// ── System cards ──────────────────────────────────────────────────────

async function loadSystems() {
    const res = await fetch('/api/systems');
    if (!res.ok) {
        showError('Failed to load systems from API');
        return;
    }
    const systems = await res.json();
    const container = document.getElementById('system-cards');

    for (const s of systems) {
        const card = document.createElement('div');
        card.className = 'system-card';
        card.dataset.systemId = s.id;
        card.innerHTML = `
            <div class="card-icon">${SYSTEM_ICONS[s.id] ?? ''}</div>
            <div class="card-name">${s.name}</div>
            <div class="card-country">${s.country}</div>
            <div class="card-desc">${s.description}</div>
        `;
        card.addEventListener('click', () => selectCard(card));
        container.appendChild(card);
    }

    const first = container.querySelector('.system-card');
    if (first) selectCard(first);
}

function selectCard(card) {
    document.querySelectorAll('.system-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
}

// ── Inputs ────────────────────────────────────────────────────────────

function readInputs() {
    const selected = document.querySelector('.system-card.selected');
    return {
        system_id:        selected?.dataset.systemId ?? '',
        n_threats:        parseInt(document.getElementById('n-threats').value, 10),
        inventory:        parseInt(document.getElementById('inventory').value, 10),
        launch_angle_deg: parseFloat(document.getElementById('launch-angle').value),
        zone_width:       parseFloat(document.getElementById('zone-width').value),
    };
}

// ── Simulation ────────────────────────────────────────────────────────

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
    document.getElementById('r-time').textContent        = response.final_time.toFixed(1) + ' s';
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
    setupSliders();
    loadSystems();
    btn.addEventListener('click', runSimulation);
});
