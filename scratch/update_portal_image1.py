import re

portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Remove the text line under the canvas:
code = re.sub(
    r'<div id="visualizer-status-text"[^>]*>.*?</div>',
    '',
    code,
    flags=re.DOTALL
)

# 2. Replace visualizer in JS
old_vis_pattern = r'// 3D Face & Connectivity Engine.*?requestAnimationFrame\(renderVisualizer\);'

new_vis_code = r'''// 3D Humanoid Hologram Head (Image 1) & Connectivity Engine
    const headSlices = [];
    const numSlices = 58;
    for (let i = 0; i < numSlices; i++) {
        const tSlice = i / (numSlices - 1);
        const y = -105 + tSlice * 220;
        let radX, radZ, zCenter = 0, feature = "head";
        if (y < -60) {
            const tc = (y - (-105)) / 45.0;
            radX = 55 * Math.sin(tc * Math.PI * 0.5);
            radZ = 62 * Math.sin(tc * Math.PI * 0.5);
            zCenter = -5; feature = "cranium";
        } else if (y < -25) {
            radX = 56; radZ = 64; zCenter = 0; feature = "forehead";
        } else if (y < -5) {
            radX = 54; radZ = 58; zCenter = 2; feature = "eyes";
        } else if (y < 25) {
            radX = 50 - (y - (-5)) * 0.2; radZ = 55; zCenter = 8; feature = "nose";
        } else if (y < 55) {
            radX = 42 - (y - 25) * 0.2; radZ = 48; zCenter = 10; feature = "mouth";
        } else if (y < 85) {
            const tj = (y - 55) / 30.0;
            radX = 36 * (1.0 - tj * 0.45); radZ = 42 * (1.0 - tj * 0.35); zCenter = 8 * (1.0 - tj); feature = "jaw";
        } else {
            const tn = (y - 85) / 30.0;
            radX = 22 + tn * 26; radZ = 24 + tn * 16; zCenter = -10; feature = "neck";
        }
        headSlices.push({ y, radX: Math.max(1, radX), radZ: Math.max(1, radZ), zCenter, feature });
    }

    const ambientParticles = [];
    for (let i = 0; i < 35; i++) {
        ambientParticles.push({
            x: (Math.random() - 0.5) * 160,
            y: (Math.random() - 0.5) * 230,
            z: (Math.random() - 0.5) * 100,
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

        const isProcessing = (currentAgentState === "THINKING" || currentAgentState === "PROCESSING");

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
            for (const [px, py, pz] of proj) {
                const r = Math.max(3, 5.5 + pz * 0.04);
                ctx.fillStyle = pz > 0 ? "#c084fc" : "#6b21a8";
                ctx.strokeStyle = pz > 15 ? "#00f0ff" : "#818cf8";
                ctx.lineWidth = 1.5;
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
            // Render 3D Dense Holographic Particle Scan-Line Head (Image 1)
            const yaw = Math.sin(t3d * 0.55) * 0.18;
            const pitch = Math.cos(t3d * 0.40) * 0.09;
            const isSpeaking = (currentAgentState === "SPEAKING");

            let mouthOpen = 0.0;
            if (isSpeaking) {
                mouthOpen = (Math.sin(t3d * 14) * 0.5 + 0.5) * 12.0 + (Math.sin(t3d * 22) * 0.3) * 5.0;
            }

            const scanWaveY = Math.sin(t3d * 2.2) * 75.0;

            // Ambient particles (glittering cyber dust)
            for (const p of ambientParticles) {
                const pyLive = p.y + Math.sin(t3d * p.speed + p.phase) * 10;
                const [px, py, pz] = project3D(p.x, pyLive, p.z, yaw, pitch, cx, cy);
                const alpha = (Math.sin(t3d * 3.2 + p.phase) + 1.0) / 2.0;
                if (alpha > 0.35) {
                    ctx.fillStyle = alpha > 0.75 ? "#e0f7fa" : "#38bdf8";
                    ctx.beginPath();
                    ctx.arc(px, py, alpha > 0.75 ? 1.5 : 1.0, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // Render Horizontal Scan-Line Slices
            for (let sIdx = 0; sIdx < headSlices.length; sIdx++) {
                const s = headSlices[sIdx];
                let yBase = s.y;
                if (s.feature === "mouth") yBase += mouthOpen * 0.5;
                else if (s.feature === "jaw") yBase += mouthOpen * 0.85;

                const pts = [];
                const numPts = 20;
                for (let pi = 0; pi < numPts; pi++) {
                    const th = -Math.PI * 0.5 + (pi / (numPts - 1)) * Math.PI;
                    let px = s.radX * Math.sin(th);
                    let pz = s.zCenter + s.radZ * Math.cos(th);

                    if (s.feature === "nose" && Math.abs(th) < 0.35) {
                        pz += 15.0 * Math.cos(th / 0.35 * (Math.PI / 2));
                    } else if (s.feature === "eyes" && Math.abs(th) > 0.25 && Math.abs(th) < 0.75) {
                        pz -= 10.0 * Math.sin((Math.abs(th) - 0.25) / 0.5 * Math.PI);
                    } else if (s.feature === "mouth" && Math.abs(th) < 0.4) {
                        pz += 8.0 * Math.cos(th / 0.4 * (Math.PI / 2));
                    } else if (s.feature === "jaw" && Math.abs(th) < 0.4) {
                        pz += 7.0 * Math.cos(th / 0.4 * (Math.PI / 2));
                    }

                    pts.push(project3D(px, yBase, pz, yaw, pitch, cx, cy));
                }

                const distToWave = Math.abs(yBase - scanWaveY);
                const isWaveHighlight = distToWave < 18.0;

                for (let seg = 0; seg < pts.length - 1; seg++) {
                    const [x1, y1, z1] = pts[seg];
                    const [x2, y2, z2] = pts[seg + 1];
                    const avgZ = (z1 + z2) / 2.0;

                    let col = "#0e7490", lw = 0.8;
                    if (isWaveHighlight && avgZ > 15) { col = "#e0f7fa"; lw = 2.0; }
                    else if (avgZ > 30) { col = "#67e8f9"; lw = 1.6; }
                    else if (avgZ > 6) { col = "#06b6d4"; lw = 1.2; }
                    else if (avgZ > -18) { col = "#0891b2"; lw = 1.0; }

                    ctx.strokeStyle = col;
                    ctx.lineWidth = lw;
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();

                    // Sparkling point-cloud dots matching Image 1
                    if (seg % 3 === 0 && avgZ > 10) {
                        const sparkle = Math.sin(t3d * 4.0 + sIdx * 0.7 + seg);
                        if (sparkle > 0.45) {
                            ctx.fillStyle = sparkle > 0.82 ? "#ffffff" : "#67e8f9";
                            ctx.beginPath();
                            ctx.arc(x1, y1, 1, 0, Math.PI * 2);
                            ctx.fill();
                        }
                    }
                }
            }
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);'''

code, count = re.subn(old_vis_pattern, new_vis_code, code, flags=re.DOTALL)
print(f"Replaced {count} occurrences of JS visualizer.")
with open(portal_path, "w", encoding="utf-8") as f:
    f.write(code)
print("Updated zen_web_portal.py successfully!")

