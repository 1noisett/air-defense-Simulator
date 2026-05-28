const CANVAS_W = 1600;
const CANVAS_H = 600;
const MARGIN = 40;

const COLORS = {
    ground:      '#4a5568',
    zone:        'rgba(252, 129, 129, 0.25)',
    zone_border: '#fc8181',
    battery:     '#e2e8f0',
    threat:      '#fc8181',
    interceptor: '#68d391',
    hud_text:    '#e2e8f0',
};

const canvas = document.getElementById('sim-canvas');
const ctx = canvas.getContext('2d');

// ── Module state ──────────────────────────────────────────────────────
let _rafId           = null;
let _paused          = false;
let _speedMultiplier = 1.0;
let _activeExplosions = [];
let _exploredThreats  = new Set();
let _wallTime         = 0;

// ── Deterministic star field (generated once at module load) ──────────

function _seededRng(seed) {
    let s = seed >>> 0;
    return () => {
        s = Math.imul(s, 1664525) + 1013904223 >>> 0;
        return s / 0x100000000;
    };
}

const _stars = (() => {
    const rng   = _seededRng(0x4e9f2a7b);   // fixed seed → same stars every load
    const stars = [];
    const N     = 80;
    for (let i = 0; i < N; i++) {
        const twinkle = i < 15;
        stars.push({
            x:      rng() * CANVAS_W,
            y:      rng() * CANVAS_H * 0.72,   // upper 72 % — above typical trajectories
            r:      0.5 + rng() * 1.0,          // 0.5 – 1.5 px
            opacity: 0.3 + rng() * 0.6,         // 0.3 – 0.9
            twinkle,
            phase:  rng() * Math.PI * 2,
        });
    }
    return stars;
})();

// ── Public controls ───────────────────────────────────────────────────

export function togglePause() {
    _paused = !_paused;
}

export function setSpeed(multiplier) {
    _speedMultiplier = multiplier;
}

// ── Main animation entry point ────────────────────────────────────────

export function animate(response, onFrame) {
    if (_rafId !== null) {
        cancelAnimationFrame(_rafId);
        _rafId = null;
    }

    _paused = false;
    _activeExplosions = [];
    _exploredThreats = new Set();

    const bounds = computeBounds(response);
    const transform = buildTransform(bounds);
    // Base scale: full animation plays in 5 wall-clock seconds at 1×
    const timeScale = Math.max(response.final_time / 5.0, 0.1);

    const indexCache = {};
    for (const traj of response.trajectories) {
        indexCache[traj.entity_id] = 0;
    }

    let _lastTs = null;
    let _currentSimTime = 0;

    function frame(ts) {
        _wallTime = ts / 1000;

        if (_lastTs === null) _lastTs = ts;
        const wallDt = (ts - _lastTs) / 1000;
        _lastTs = ts;

        if (!_paused) {
            _currentSimTime = Math.min(
                _currentSimTime + wallDt * timeScale * _speedMultiplier,
                response.final_time,
            );
        }

        detectExplosions(_currentSimTime, response, transform);
        drawScene(_currentSimTime, response, transform, indexCache);
        if (onFrame) onFrame(_currentSimTime);

        if (_currentSimTime < response.final_time) {
            _rafId = requestAnimationFrame(frame);
        } else {
            _rafId = null;
        }
    }

    _rafId = requestAnimationFrame(frame);
}

// ── Coordinate math ───────────────────────────────────────────────────

function computeBounds(response) {
    // Hard ceilings derived from known geometry. An outlier trajectory (e.g.
    // a divergent interceptor) is allowed to leave the visible area instead
    // of inflating the scale and squashing everything else into a few pixels.
    const X_CEILING = response.battery_position.x * 1.10;
    const Y_CEILING = 800;

    let xMax = response.battery_position.x;
    let yMax = 100;

    xMax = Math.max(xMax, response.protected_zone.x_max);

    for (const traj of response.trajectories) {
        for (const s of traj.snapshots) {
            if (s.x > xMax && s.x <= X_CEILING) xMax = s.x;
            if (s.y > yMax && s.y <= Y_CEILING) yMax = s.y;
        }
    }

    return { xMax, yMax };
}

function buildTransform(bounds) {
    const scaleX = (CANVAS_W - 2 * MARGIN) / bounds.xMax;
    const scaleY = (CANVAS_H - 2 * MARGIN) / bounds.yMax;
    const scale = Math.min(scaleX, scaleY);
    return { scale };
}

function worldToCanvas(wx, wy, t) {
    const cx = MARGIN + wx * t.scale;
    const cy = CANVAS_H - MARGIN - wy * t.scale;
    return [cx, cy];
}

// Returns snapshot at or just before simTime; null if entity not yet launched.
// Advances index incrementally — O(1) amortised.
function getSnapshotAtTime(snapshots, simTime, indexCache, entityId) {
    if (simTime < snapshots[0].t) return null;

    let idx = indexCache[entityId];
    while (idx + 1 < snapshots.length && snapshots[idx + 1].t <= simTime) {
        idx++;
    }
    indexCache[entityId] = idx;
    return snapshots[idx];
}

// ── Background: night sky ─────────────────────────────────────────────

function drawBackground() {
    // Sky gradient: deep night → slightly lighter near horizon → dark ground
    const grad = ctx.createLinearGradient(0, 0, 0, CANVAS_H);
    grad.addColorStop(0,    '#0a0e1a');
    grad.addColorStop(0.80, '#1a2332');
    grad.addColorStop(1.0,  '#0d1117');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    // Stars
    for (const star of _stars) {
        let alpha = star.opacity;
        if (star.twinkle) {
            // Slow, very subtle opacity oscillation
            alpha = star.opacity * (0.72 + 0.28 * Math.sin(_wallTime * 1.4 + star.phase));
        }
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.r, 0, 2 * Math.PI);
        ctx.fillStyle = `rgba(220,235,255,${alpha.toFixed(3)})`;
        ctx.fill();
    }
}

// ── Scene drawing ─────────────────────────────────────────────────────

function drawScene(simTime, response, transform, indexCache) {
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    // Order: sky → stars → ground band → ground line → zone → battery → entities → explosions → HUD
    drawBackground();
    drawGroundBand(transform);
    drawGroundLine();
    drawProtectedZone(response, transform);
    drawBattery(response, transform);

    for (const traj of response.trajectories) {
        drawEntity(traj, simTime, transform, indexCache);
    }

    drawExplosions(simTime);
}

function drawGroundBand(transform) {
    // Dark earth strip below the ground line
    const groundY = CANVAS_H - MARGIN;
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, groundY, CANVAS_W, CANVAS_H - groundY);
}

function drawGroundLine() {
    ctx.beginPath();
    ctx.moveTo(MARGIN, CANVAS_H - MARGIN);
    ctx.lineTo(CANVAS_W - MARGIN, CANVAS_H - MARGIN);
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
    const size = 10;

    ctx.beginPath();
    ctx.moveTo(cx, cy - size);
    ctx.lineTo(cx + size, cy + size);
    ctx.lineTo(cx - size, cy + size);
    ctx.closePath();

    ctx.shadowBlur  = 10;
    ctx.shadowColor = COLORS.battery;
    ctx.fillStyle   = COLORS.battery;
    ctx.fill();
    ctx.shadowBlur  = 0;
    ctx.shadowColor = 'transparent';
}

function drawEntity(traj, simTime, transform, indexCache) {
    const snap = getSnapshotAtTime(traj.snapshots, simTime, indexCache, traj.entity_id);
    if (snap === null) return;

    const color = traj.entity_type === 'threat' ? COLORS.threat : COLORS.interceptor;
    const currentIdx = indexCache[traj.entity_id];
    const snapshots = traj.snapshots;

    // Trail
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

    // Current position dot with glow
    const [px, py] = worldToCanvas(snap.x, snap.y, transform);
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, 2 * Math.PI);
    ctx.fillStyle   = color;
    ctx.shadowBlur  = 12;
    ctx.shadowColor = color;
    ctx.fill();
    ctx.shadowBlur  = 0;
    ctx.shadowColor = 'transparent';
}

// ── Explosions ────────────────────────────────────────────────────────

function detectExplosions(simTime, response, transform) {
    for (const traj of response.trajectories) {
        if (traj.entity_type !== 'threat') continue;
        if (traj.disposition !== 'neutralized') continue;
        if (_exploredThreats.has(traj.entity_id)) continue;

        const last = traj.snapshots[traj.snapshots.length - 1];
        if (simTime >= last.t) {
            _exploredThreats.add(traj.entity_id);
            const [ex, ey] = worldToCanvas(last.x, last.y, transform);
            _activeExplosions.push({ x: ex, y: ey, startTime: simTime, duration: 0.4 });
        }
    }
}

function drawExplosions(simTime) {
    _activeExplosions = _activeExplosions.filter(
        exp => simTime - exp.startTime < exp.duration
    );

    const rings = [
        { delay: 0.00, color: '#fefcbf', maxR: 30 },
        { delay: 0.08, color: '#f6ad55', maxR: 22 },
        { delay: 0.16, color: '#dd6b20', maxR: 15 },
    ];

    for (const exp of _activeExplosions) {
        const t = (simTime - exp.startTime) / exp.duration;

        for (const ring of rings) {
            const rt = Math.max(0, t - ring.delay);
            if (rt <= 0) continue;
            const radius = 5 + rt * ring.maxR;
            const alpha  = Math.max(0, 1.0 - rt);

            ctx.beginPath();
            ctx.arc(exp.x, exp.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle  = ring.color;
            ctx.globalAlpha = alpha;
            ctx.fill();
        }
        ctx.globalAlpha = 1.0;
    }
}

