import os

portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add static route for /static/hologram_face.png if not present
if '/static/hologram_face.png' not in code:
    route_target = '@app.get("/api/status")'
    static_route = '''@app.get("/static/hologram_face.png")
async def get_hologram_face():
    """Serves the real 3D blended hologram face texture matching Image 1."""
    face_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "hologram_face.png")
    if os.path.exists(face_path):
        with open(face_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    raise HTTPException(status_code=404, detail="Hologram face texture not found")

@app.get("/api/status")'''
    code = code.replace(route_target, static_route, 1)

# 2. Update JavaScript visualizer in zen_web_portal.py
# Find start of visualizer setup and end of renderVisualizer
js_start_marker = "// 3D Humanoid Hologram Head (Image 1) & Connectivity Engine"
js_end_marker = "function setAgentState(state) {"

js_start = code.find(js_start_marker)
js_end = code.find(js_end_marker)

assert js_start != -1, "js_start_marker not found"
assert js_end != -1, "js_end_marker not found"

new_js = '''// Real 3D Blended Hologram Face & Connectivity Engine
    const faceImg = new Image();
    faceImg.src = "/static/hologram_face.png";
    let faceLoaded = false;
    faceImg.onload = () => { faceLoaded = true; };

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
            // Render Real Photorealistic 3D Blended Hologram Face (matching Image 1)
            const breathe = Math.sin(t3d * 1.4);
            const yFloat = breathe * 4.0;
            const scale = 0.88 + 0.015 * breathe;
            const rotAngle = Math.sin(t3d * 0.7) * 0.035;

            // Holographic Aura Rings
            const rRing = 80 + Math.sin(t3d * 2.0) * 4;
            const arcAng = (t3d * 0.5) % (Math.PI * 2);
            ctx.strokeStyle = "#0d2137";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(cx, cy + yFloat, rRing, 0, Math.PI * 2);
            ctx.stroke();

            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 2.0;
            ctx.beginPath();
            ctx.arc(cx, cy + yFloat, rRing + 2, arcAng, arcAng + 1.1);
            ctx.stroke();

            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.arc(cx, cy + yFloat, rRing + 2, arcAng + Math.PI, arcAng + Math.PI + 0.8);
            ctx.stroke();

            // Ambient Cyber Glitter Particles
            for (const p of ambientParticles) {
                const pyLive = p.y + Math.sin(t3d * p.speed + p.phase) * 8;
                const alpha = (Math.sin(t3d * 3.0 + p.phase) + 1.0) / 2.0;
                if (alpha > 0.4) {
                    ctx.fillStyle = alpha > 0.75 ? "#e0f7fa" : "#38bdf8";
                    ctx.beginPath();
                    ctx.arc(cx + p.x, cy + yFloat + pyLive, alpha > 0.75 ? 1.5 : 1.0, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // Draw Real Blended Hologram Face Image
            if (faceLoaded && faceImg.width > 0) {
                ctx.save();
                ctx.translate(cx, cy + yFloat);
                ctx.rotate(rotAngle);
                const drawH = 175 * scale;
                const drawW = (faceImg.width / faceImg.height) * drawH;
                ctx.drawImage(faceImg, -drawW / 2, -drawH / 2, drawW, drawH);

                // Vertical Luminescence Laser Scanline Wave
                const scanY = Math.sin(t3d * 2.2) * (drawH * 0.40);
                ctx.strokeStyle = "#e0f7fa";
                ctx.lineWidth = 2.0;
                ctx.beginPath();
                ctx.moveTo(-drawW * 0.38, scanY);
                ctx.lineTo(drawW * 0.38, scanY);
                ctx.stroke();

                ctx.strokeStyle = "#00f0ff";
                ctx.lineWidth = 1.0;
                ctx.beginPath();
                ctx.moveTo(-drawW * 0.45, scanY);
                ctx.lineTo(drawW * 0.45, scanY);
                ctx.stroke();

                ctx.restore();
            }

            // Radiating Speech Waves during Speaking
            if (currentAgentState === "SPEAKING") {
                for (let rip = 0; rip < 3; rip++) {
                    const ripR = rRing + ((t3d * 50 + rip * 30) % 60);
                    const ripAlpha = 1.0 - (ripR - rRing) / 60.0;
                    if (ripAlpha > 0.05) {
                        ctx.strokeStyle = rip % 2 === 0 ? "rgba(0, 240, 255, " + ripAlpha + ")" : "rgba(56, 189, 248, " + ripAlpha + ")";
                        ctx.lineWidth = 1.5;
                        ctx.beginPath();
                        ctx.arc(cx, cy + yFloat, ripR, 0, Math.PI * 2);
                        ctx.stroke();
                    }
                }
            }
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);

    '''

code = code[:js_start] + new_js + code[js_end:]

# Safely guard visualizerStatus
old_set_state = "visualizerStatus.textContent = map[currentAgentState] || (\"STATE: \" + currentAgentState);"
new_set_state = "if (visualizerStatus) { visualizerStatus.textContent = map[currentAgentState] || (\"STATE: \" + currentAgentState); }"
code = code.replace(old_set_state, new_set_state)

with open(portal_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated zen_web_portal.py successfully.")

