import os

portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    portal_code = f.read()

# 1. Add static route for /static/head_scanlines.json if not present
if '/static/head_scanlines.json' not in portal_code:
    route_target = '@app.get("/static/hologram_face.png")'
    static_route = '''@app.get("/static/head_scanlines.json")
async def get_head_scanlines():
    """Serves real 3D head scanline mesh points."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "head_scanlines.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="application/json")
    raise HTTPException(status_code=404, detail="Head scanlines not found")

@app.get("/static/hologram_face.png")'''
    portal_code = portal_code.replace(route_target, static_route, 1)

# 2. Update JavaScript visualizer in zen_web_portal.py
p_start_marker = "// Real 3D Blended Hologram Face & Connectivity Engine"
p_end_marker = "function setAgentState(state) {"

p_start = portal_code.find(p_start_marker)
p_end = portal_code.find(p_end_marker)

assert p_start != -1, "portal visualizer marker not found"
assert p_end != -1, "portal setAgentState marker not found"

new_portal_visualizer = '''// Real 3D Humanoid Head Mesh & Connectivity Engine
    let headPoints = null;
    const numSlices = 90;
    const ptsPerRing = 75;

    fetch("/static/head_scanlines.json")
        .then(r => r.json())
        .then(data => {
            headPoints = new Float32Array(data.flat());
        })
        .catch(err => console.error("Error loading 3D head mesh:", err));

    // Organic Gaze & Angle Tracking
    let currentYaw = 0.0, currentPitch = 0.0, currentRoll = 0.0, currentDx = 0.0, currentDy = 0.0;
    let targetYaw = 0.0, targetPitch = 0.0, targetRoll = 0.0, targetDx = 0.0, targetDy = 0.0;
    let nextGazeTime = Date.now() + 1000;

    const ambientParticles = [];
    for (let i = 0; i < 35; i++) {
        ambientParticles.push({
            x: (Math.random() - 0.5) * 160,
            y: (Math.random() - 0.5) * 170,
            speed: 0.3 + Math.random() * 0.6,
            phase: Math.random() * Math.PI * 2
        });
    }

    const phi = (1 + Math.sqrt(5)) / 2;
    const rawNodes = [
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
    ];
    const connectNodes = rawNodes.map(([x, y, z]) => [x * 46, y * 46, z * 46]);
    const connectEdges = [];
    for (let i = 0; i < connectNodes.length; i++) {
        for (let j = i + 1; j < connectNodes.length; j++) {
            const [x1, y1, z1] = connectNodes[i];
            const [x2, y2, z2] = connectNodes[j];
            const d = Math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2);
            if (d < 110) connectEdges.push([i, j]);
        }
    }

    function project3D(x, y, z, yaw, pitch, cx, cy) {
        const cosY = Math.cos(yaw), sinY = Math.sin(yaw);
        const x1 = x * cosY + z * sinY;
        const z1 = -x * sinY + z * cosY;
        const cosX = Math.cos(pitch), sinX = Math.sin(pitch);
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;
        const fov = 380, dist = 320;
        const factor = fov / (z2 + dist);
        return [cx + x1 * factor, cy + y2 * factor, z2];
    }

    let t3d = 0.0;

    function renderVisualizer() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        t3d += 0.05;

        const isProcessing = (currentAgentState === "THINKING" || currentAgentState === "PROCESSING" || currentAgentState === "EXECUTING");

        if (isProcessing) {
            // Render 3D Connectivity Working Cluster
            const yaw = t3d * 0.95, pitch = t3d * 0.70;
            const proj = connectNodes.map(([x, y, z]) => project3D(x, y, z, yaw, pitch, cx, cy));

            // Gyroscopic Rings
            ctx.strokeStyle = "#c084fc";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th), 120 * Math.sin(th) * 0.35, 0, yaw * 1.5, pitch, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            ctx.strokeStyle = "#38bdf8";
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th) * 0.35, 120 * Math.sin(th), 0, -yaw * 1.3, pitch * 1.4, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            // Connections
            for (const [i1, i2] of connectEdges) {
                const [x1, y1, z1] = proj[i1];
                const [x2, y2, z2] = proj[i2];
                ctx.strokeStyle = (z1 + z2 > 0) ? "#a855f7" : "#4c1d95";
                ctx.lineWidth = (z1 + z2 > 10) ? 2 : 1;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }

            // Data Packets traveling
            for (let p = 0; p < 12; p++) {
                const [i1, i2] = connectEdges[(p * 3) % connectEdges.length];
                const [x1, y1] = proj[i1];
                const [x2, y2] = proj[i2];
                const prog = (t3d * 2.5 + p * 0.4) % 1.0;
                const pakX = x1 + (x2 - x1) * prog;
                const pakY = y1 + (y2 - y1) * prog;
                ctx.fillStyle = "#00f0ff";
                ctx.beginPath();
                ctx.arc(pakX, pakY, 3, 0, Math.PI * 2);
                ctx.fill();
            }

            // Nodes
            const sortedNodes = proj.map((p, i) => ({ p, i })).sort((a, b) => a.p[2] - b.p[2]);
            for (const item of sortedNodes) {
                const [px, py, pz] = item.p;
                const r = Math.max(3, 5.5 + pz * 0.035);
                ctx.fillStyle = pz > 0 ? "#c084fc" : "#6b21a8";
                ctx.strokeStyle = pz > 10 ? "#00f0ff" : "#818cf8";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(px, py, r, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
            }

            // Power core
            ctx.fillStyle = "#0d1b2a";
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, 14, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#00f0ff";
            ctx.font = "bold 11px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("⚡", cx, cy);

        } else {
            // Render True 3D Head Object with continuous cyber scanlines & organic gaze
            const now = Date.now();
            const isSpeaking = (currentAgentState === "SPEAKING");

            if (isSpeaking) {
                targetYaw = Math.sin(t3d * 3.2) * 0.10;
                targetPitch = Math.sin(t3d * 4.5) * 0.06;
                targetRoll = Math.sin(t3d * 2.5) * 0.04;
                targetDx = Math.sin(t3d * 2.0) * 6.0;
                targetDy = Math.sin(t3d * 2.8) * 4.0;
                nextGazeTime = now + 1200;
            } else if (now >= nextGazeTime) {
                if (Math.random() < 0.28) {
                    targetYaw = (Math.random() - 0.5) * 0.10;
                    targetPitch = (Math.random() - 0.5) * 0.08;
                    targetRoll = (Math.random() - 0.5) * 0.04;
                    targetDx = (Math.random() - 0.5) * 10;
                    targetDy = (Math.random() - 0.5) * 8;
                    nextGazeTime = now + 1800 + Math.random() * 1400;
                } else {
                    targetYaw = (Math.random() > 0.5 ? 1 : -1) * (0.18 + Math.random() * 0.28);
                    targetPitch = (Math.random() - 0.5) * 0.44;
                    targetRoll = -targetYaw * (0.15 + Math.random() * 0.15);
                    targetDx = targetYaw * 35.0;
                    targetDy = targetPitch * 22.0;
                    nextGazeTime = now + 2000 + Math.random() * 2200;
                }
            }

            const lerp = 0.055;
            currentYaw += (targetYaw - currentYaw) * lerp;
            currentPitch += (targetPitch - currentPitch) * lerp;
            currentRoll += (targetRoll - currentRoll) * lerp;
            currentDx += (targetDx - currentDx) * lerp;
            currentDy += (targetDy - currentDy) * lerp;

            const breathe = Math.sin(t3d * 1.5);
            const yBreathe = breathe * 3.5;
            const scale = 0.72 + 0.012 * breathe;

            // Ambient Cyber Glitter Particles
            for (const p of ambientParticles) {
                const pyLive = p.y + Math.sin(t3d * p.speed + p.phase) * 8;
                const alpha = (Math.sin(t3d * 3.0 + p.phase) + 1.0) / 2.0;
                if (alpha > 0.4) {
                    ctx.fillStyle = alpha > 0.75 ? "#e0f7fa" : "#38bdf8";
                    ctx.beginPath();
                    ctx.arc(cx + p.x, cy + pyLive, alpha > 0.75 ? 1.5 : 1.0, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // Draw Real 3D Head Object Scanlines
            if (headPoints !== null) {
                const cosY = Math.cos(currentYaw), sinY = Math.sin(currentYaw);
                const cosX = Math.cos(currentPitch), sinX = Math.sin(currentPitch);
                const cosZ = Math.cos(currentRoll), sinZ = Math.sin(currentRoll);
                const fov = 350.0, dist = 280.0;
                const liveCx = cx + currentDx;
                const liveCy = cy + currentDy + yBreathe;

                const mouthOpen = isSpeaking ? (Math.sin(t3d * 16) * 0.5 + 0.5) * 7.0 : 0.0;
                const totalPts = numSlices * ptsPerRing;

                // Project points
                const projX = new Float32Array(totalPts);
                const projY = new Float32Array(totalPts);
                const projZ = new Float32Array(totalPts);

                for (let i = 0; i < totalPts; i++) {
                    let ox = headPoints[i * 3] * scale;
                    let oy = headPoints[i * 3 + 1] * scale;
                    let oz = headPoints[i * 3 + 2] * scale;

                    if (isSpeaking && oy > 25 && oy < 65 && oz > 0) {
                        const tj = (oy - 25) / 40.0;
                        oy += mouthOpen * Math.sin(tj * Math.PI);
                    }

                    // Yaw
                    const x1 = ox * cosY + oz * sinY;
                    const z1 = -ox * sinY + oz * cosY;
                    // Pitch
                    const y2 = oy * cosX - z1 * sinX;
                    const z2 = oy * sinX + z1 * cosX;
                    // Roll
                    const x3 = x1 * cosZ - y2 * sinZ;
                    const y3 = x1 * sinZ + y2 * cosZ;

                    const factor = fov / (z2 + dist);
                    projX[i] = liveCx + x3 * factor;
                    projY[i] = liveCy + y3 * factor;
                    projZ[i] = z2;
                }

                // Render rings
                for (let s = 0; s < numSlices; s++) {
                    const startIdx = s * ptsPerRing;
                    for (let i = 0; i < ptsPerRing - 1; i++) {
                        const idx1 = startIdx + i;
                        const idx2 = idx1 + 1;
                        const zAvg = (projZ[idx1] + projZ[idx2]) / 2.0;

                        if (zAvg < -18.0) continue;

                        const x1 = projX[idx1], y1 = projY[idx1];
                        const x2 = projX[idx2], y2 = projY[idx2];
                        const segDist = Math.hypot(x2 - x1, y2 - y1);
                        if (segDist > 14.0) continue;

                        let col = "rgba(14, 116, 144, 0.4)";
                        let lw = 1;
                        if (zAvg > 30) { col = "rgba(220, 248, 255, 0.95)"; lw = 1.8; }
                        else if (zAvg > 15) { col = "rgba(103, 232, 249, 0.85)"; lw = 1.2; }
                        else if (zAvg > 0) { col = "rgba(6, 182, 212, 0.70)"; lw = 1.0; }
                        else if (zAvg > -10) { col = "rgba(8, 145, 178, 0.50)"; lw = 1.0; }

                        ctx.strokeStyle = col;
                        ctx.lineWidth = lw;
                        ctx.beginPath();
                        ctx.moveTo(x1, y1);
                        ctx.lineTo(x2, y2);
                        ctx.stroke();

                        if (i % 3 === 0 && zAvg > 2) {
                            const twinkle = Math.sin(t3d * 4.2 + s * 0.7 + i);
                            if (twinkle > 0.45) {
                                ctx.fillStyle = (zAvg > 25 && twinkle > 0.8) ? "#ffffff" : "#67e8f9";
                                ctx.beginPath();
                                ctx.arc(x1, y1, zAvg > 25 ? 1.2 : 0.8, 0, Math.PI * 2);
                                ctx.fill();
                            }
                        }
                    }
                }
            }
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);

    '''

portal_code = portal_code[:p_start] + new_portal_visualizer + portal_code[p_end:]
with open(portal_path, "w", encoding="utf-8") as f:
    f.write(portal_code)
print("Updated zen_web_portal.py successfully with Real 3D Head Scanlines Mesh!")

