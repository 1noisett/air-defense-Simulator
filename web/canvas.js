const CANVAS_W = 800;
const CANVAS_H = 500;
const MARGIN = 40;

const COLORS = {
    bg:          '#f7fafc',
    ground:      '#a0aec0',
    zone:        'rgba(229, 62, 62, 0.2)',
    zone_border: '#e53e3e',
    battery:     '#2d3748',
    threat:      '#e53e3e',
    interceptor: '#38a169',
    hud_text:    '#1a202c',
};

const canvas = document.getElementById('sim-canvas');
const ctx = canvas.getContext('2d');

let _rafId = null;

export function animate(response) {
    if (_rafId !== null) {
        cancelAnimationFrame(_rafId);
        _rafId = null;
    }

    const bounds = computeBounds(response);
    const transform = buildTransform(bounds);
    // Defensive: prevent freeze if final_time is 0 or near-zero
    const timeScale = Math.max(response.final_time / 5.0, 0.1);

    // Initialize snapshot index cache to 0 for every entity
    const indexCache = {};
    for (const traj of response.trajectories) {
        indexCache[traj.entity_id] = 0;
    }

    let startTs = null;

    function frame(ts) {
        if (startTs === null) startTs = ts;
        const simTime = Math.min(
            ((ts - startTs) / 1000) * timeScale,
            response.final_time,
        );

        drawScene(simTime, response, transform, indexCache);

        if (simTime < response.final_time) {
            _rafId = requestAnimationFrame(frame);
        } else {
            _rafId = null;
        }
    }

    _rafId = requestAnimationFrame(frame);
}

function computeBounds(response) {
    let xMax = response.battery_position.x;
    let yMax = 100; // minimum so the zone (y_max=30) is always visible

    xMax = Math.max(xMax, response.protected_zone.x_max);

    for (const traj of response.trajectories) {
        for (const s of traj.snapshots) {
            if (s.x > xMax) xMax = s.x;
            if (s.y > yMax) yMax = s.y;
        }
    }

    return { xMax, yMax };
}

function buildTransform(bounds) {
    const scaleX = (CANVAS_W - 2 * MARGIN) / bounds.xMax;
    const scaleY = (CANVAS_H - 2 * MARGIN) / bounds.yMax;
    // Uniform scale preserves parabola aspect ratio (no distortion)
    const scale = Math.min(scaleX, scaleY);
    return { scale };
}

function worldToCanvas(wx, wy, t) {
    const cx = MARGIN + wx * t.scale;
    // Canvas y=0 is at top; world y=0 is at bottom — invert
    const cy = CANVAS_H - MARGIN - wy * t.scale;
    return [cx, cy];
}

// Returns the snapshot at or just before simTime, or null if entity not yet launched.
// Advances index incrementally — O(1) amortized over the full animation.
function getSnapshotAtTime(snapshots, simTime, indexCache, entityId) {
    if (simTime < snapshots[0].t) return null; // not launched yet

    let idx = indexCache[entityId];
    while (idx + 1 < snapshots.length && snapshots[idx + 1].t <= simTime) {
        idx++;
    }
    indexCache[entityId] = idx;
    return snapshots[idx];
}

function drawScene(simTime, response, transform, indexCache) {
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    // Background
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    drawGround(transform);
    drawProtectedZone(response, transform);
    drawBattery(response, transform);

    for (const traj of response.trajectories) {
        drawEntity(traj, simTime, transform, indexCache);
    }

    drawHUD(simTime);
}

function drawGround(transform) {
    const [x0, y0] = worldToCanvas(0, 0, transform);
    const [x1]     = worldToCanvas(transform.scale === 0 ? CANVAS_W : (CANVAS_W - MARGIN) / transform.scale, 0, transform);
    ctx.beginPath();
    ctx.moveTo(MARGIN, y0);
    ctx.lineTo(CANVAS_W - MARGIN, y0);
    ctx.strokeStyle = COLORS.ground;
    ctx.lineWidth = 2;
    ctx.stroke();
}

function drawProtectedZone(response, transform) {
    const z = response.protected_zone;
    const [x0, y0] = worldToCanvas(z.x_min, z.y_max, transform);
    const [x1, y1] = worldToCanvas(z.x_max, z.y_min, transform);
    const w = x1 - x0;
    const h = y1 - y0;

    ctx.fillStyle = COLORS.zone;
    ctx.fillRect(x0, y0, w, h);
    ctx.strokeStyle = COLORS.zone_border;
    ctx.lineWidth = 1;
    ctx.strokeRect(x0, y0, w, h);
}

function drawBattery(response, transform) {
    const [cx, cy] = worldToCanvas(response.battery_position.x, response.battery_position.y, transform);
    const size = 8;

    ctx.beginPath();
    ctx.moveTo(cx, cy - size);
    ctx.lineTo(cx + size, cy + size);
    ctx.lineTo(cx - size, cy + size);
    ctx.closePath();
    ctx.fillStyle = COLORS.battery;
    ctx.fill();
}

function drawEntity(traj, simTime, transform, indexCache) {
    const snap = getSnapshotAtTime(traj.snapshots, simTime, indexCache, traj.entity_id);
    if (snap === null) return; // not yet launched

    const color = traj.entity_type === 'threat' ? COLORS.threat : COLORS.interceptor;
    const currentIdx = indexCache[traj.entity_id];
    const snapshots = traj.snapshots;

    // Trail from launch point to current position
    if (currentIdx > 0) {
        ctx.beginPath();
        const [x0, y0] = worldToCanvas(snapshots[0].x, snapshots[0].y, transform);
        ctx.moveTo(x0, y0);
        for (let i = 1; i <= currentIdx; i++) {
            const [xi, yi] = worldToCanvas(snapshots[i].x, snapshots[i].y, transform);
            ctx.lineTo(xi, yi);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.5;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }

    // Current position dot
    const [px, py] = worldToCanvas(snap.x, snap.y, transform);
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
}

function drawHUD(simTime) {
    ctx.fillStyle = COLORS.hud_text;
    ctx.font = '13px monospace';
    ctx.fillText(`t = ${simTime.toFixed(2)} s`, MARGIN + 4, MARGIN + 4);
}
