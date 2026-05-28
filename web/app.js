import { animate, togglePause, setSpeed } from './canvas.js';
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
        { id: 'maneuver',     valId: 'maneuver-val',     fmt: v => `${v}%` },
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
        const maxG = (s.max_acceleration / 9.81).toFixed(0);
        card.innerHTML = `
            <div class="card-icon">${SYSTEM_ICONS[s.id] ?? ''}</div>
            <div class="card-name">${s.name}</div>
            <div class="card-country">${s.country}</div>
            <div class="card-desc">${s.description}</div>
            <div class="card-stats">
                <div class="stat"><span class="stat-key">N</span><span class="stat-val">${s.pn_constant.toFixed(1)}</span></div>
                <div class="stat"><span class="stat-key">SPD</span><span class="stat-val">${s.launch_speed.toFixed(0)} m/s</span></div>
                <div class="stat"><span class="stat-key">MAX</span><span class="stat-val">${maxG} G</span></div>
                <div class="stat"><span class="stat-key">KILL</span><span class="stat-val">${s.kill_radius.toFixed(0)} m</span></div>
            </div>
        `;
        card.addEventListener('click', () => selectCard(s));
        container.appendChild(card);
    }

    if (systems.length > 0) selectCard(systems[0]);
}

function selectCard(system) {
    document.querySelectorAll('.system-card').forEach(c => {
        c.classList.toggle('selected', c.dataset.systemId === system.id);
    });
    document.getElementById('as-name').textContent    = system.name;
    document.getElementById('as-country').textContent = system.country;
}

// ── Inputs ────────────────────────────────────────────────────────────

function readInputs() {
    const selected = document.querySelector('.system-card.selected');
    return {
        system_id:         selected?.dataset.systemId ?? '',
        n_threats:         parseInt(document.getElementById('n-threats').value, 10),
        inventory:         parseInt(document.getElementById('inventory').value, 10),
        launch_angle_deg:  parseFloat(document.getElementById('launch-angle').value),
        zone_width:        parseFloat(document.getElementById('zone-width').value),
        maneuver_intensity: parseFloat(document.getElementById('maneuver').value),
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
        resetHUD(data);
        animate(data, simTime => updateHUD(simTime, data));
        updateResults(data);
    } catch (e) {
        showError(`Network error: ${e.message}`);
    } finally {
        btn.disabled = false;
    }
}

// ── HUD (right-sidebar live telemetry) ────────────────────────────────

function totalInterceptors(response) {
    return response.trajectories.filter(t => t.entity_type === 'interceptor').length
        + response.inventory_remaining;
}

function resetHUD(response) {
    document.getElementById('hud-radar').textContent        = 'ACTIVE';
    document.getElementById('hud-clock').textContent        = '0.00 s';
    document.getElementById('hud-interceptors').textContent = `0/${totalInterceptors(response)}`;
    document.getElementById('hud-threats').textContent      = '0';
}

function updateHUD(simTime, response) {
    const interceptorTrajs = response.trajectories.filter(t => t.entity_type === 'interceptor');
    const threatTrajs      = response.trajectories.filter(t => t.entity_type === 'threat');

    const fired = interceptorTrajs.filter(
        t => t.snapshots.length > 0 && t.snapshots[0].t <= simTime
    ).length;
    const tracked = threatTrajs.filter(t => {
        const last = t.snapshots[t.snapshots.length - 1];
        return t.snapshots[0].t <= simTime && simTime < last.t;
    }).length;

    document.getElementById('hud-clock').textContent        = simTime.toFixed(2) + ' s';
    document.getElementById('hud-interceptors').textContent = `${fired}/${totalInterceptors(response)}`;
    document.getElementById('hud-threats').textContent      = tracked;
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

// ── Canvas controls ───────────────────────────────────────────────────

function setupCanvasControls() {
    const pauseBtn    = document.getElementById('pause-btn');
    const speedSlider = document.getElementById('speed-slider');
    const speedLabel  = document.getElementById('speed-label');

    pauseBtn.addEventListener('click', () => {
        togglePause();
        pauseBtn.textContent = pauseBtn.textContent === '⏸' ? '▶' : '⏸';
    });

    speedSlider.addEventListener('input', () => {
        const v = parseFloat(speedSlider.value);
        setSpeed(v);
        speedLabel.textContent = `${v}×`;
    });
}

// ── Init ──────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setupSliders();
    setupCanvasControls();
    loadSystems();
    btn.addEventListener('click', runSimulation);
});
