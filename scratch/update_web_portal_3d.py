new_js_visualizer = r'''    // 3D Face & Connectivity Engine
    const faceVerts = {
        "f_top": [0, -85, 20], "f_l1": [-38, -75, 0], "f_r1": [38, -75, 0],
        "f_l2": [-58, -55, -20], "f_r2": [58, -55, -20],
        "b_mid": [0, -32, 42], "b_l": [-32, -34, 35], "b_r": [32, -34, 35],
        "b_l_out": [-54, -28, 10], "b_r_out": [54, -28, 10],
        "e_l_in": [-14, -18, 35], "e_l_out": [-42, -18, 25], "e_l_top": [-28, -25, 30], "e_l_bot": [-28, -11, 30],
        "e_r_in": [14, -18, 35], "e_r_out": [42, -18, 25], "e_r_top": [28, -25, 30], "e_r_bot": [28, -11, 30],
        "n_bridge": [0, -14, 45], "n_tip": [0, 14, 56], "n_l": [-13, 16, 40], "n_r": [13, 16, 40],
        "c_l": [-58, 0, 0], "c_r": [58, 0, 0], "c_l_in": [-32, 14, 28], "c_r_in": [32, 14, 28],
        "lip_top": [0, 34, 44], "lip_l": [-20, 38, 35], "lip_r": [20, 38, 35],
        "lip_bot": [0, 42, 42], "jaw_l": [-50, 40, -10], "jaw_r": [50, 40, -10],
        "chin_l": [-18, 76, 28], "chin_r": [18, 76, 28], "chin_tip": [0, 82, 35]
    };

    const faceEdges = [
        ["f_l2", "f_l1"], ["f_l1", "f_top"], ["f_top", "f_r1"], ["f_r1", "f_r2"],
        ["f_l2", "b_l_out"], ["f_r2", "b_r_out"],
        ["f_top", "b_mid"], ["f_l1", "b_l"], ["f_r1", "b_r"],
        ["b_l_out", "b_l"], ["b_l", "b_mid"], ["b_mid", "b_r"], ["b_r", "b_r_out"],
        ["e_l_in", "e_l_top"], ["e_l_top", "e_l_out"], ["e_l_out", "e_l_bot"], ["e_l_bot", "e_l_in"],
        ["e_r_in", "e_r_top"], ["e_r_top", "e_r_out"], ["e_r_out", "e_r_bot"], ["e_r_bot", "e_r_in"],
        ["b_mid", "n_bridge"], ["n_bridge", "n_tip"],
        ["n_tip", "n_l"], ["n_tip", "n_r"], ["n_l", "n_bridge"], ["n_r", "n_bridge"],
        ["b_l_out", "c_l"], ["b_r_out", "c_r"],
        ["c_l", "c_l_in"], ["c_r", "c_r_in"], ["c_l_in", "n_l"], ["c_r_in", "n_r"],
        ["lip_l", "lip_top"], ["lip_top", "lip_r"], ["lip_l", "lip_bot"], ["lip_bot", "lip_r"],
        ["n_tip", "lip_top"], ["c_l", "jaw_l"], ["c_r", "jaw_r"],
        ["jaw_l", "chin_l"], ["jaw_r", "chin_r"], ["chin_l", "chin_tip"], ["chin_r", "chin_tip"],
        ["lip_bot", "chin_tip"], ["lip_l", "c_l_in"], ["lip_r", "c_r_in"]
    ];

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
            // Render 3D Talking Face
            const yaw = Math.sin(t3d * 0.75) * 0.22;
            const pitch = Math.cos(t3d * 0.55) * 0.12;
            const isSpeaking = (currentAgentState === "SPEAKING");
            const isListening = (currentAgentState === "LISTENING");

            let mouthOpen = 0.0;
            if (isSpeaking) {
                mouthOpen = (Math.sin(t3d * 14) * 0.5 + 0.5) * 16.0 + (Math.sin(t3d * 22) * 0.3) * 6.0;
            } else if (isListening) {
                mouthOpen = 2.0;
            }

            let primaryCol = "#00f0ff", glowCol = "#0284c7", eyeCol = "#38bdf8";
            if (isSpeaking) {
                primaryCol = "#00f0ff"; glowCol = "#38bdf8"; eyeCol = "#00ffcc";
            } else if (isListening) {
                primaryCol = "#fbbf24"; glowCol = "#f59e0b"; eyeCol = "#fef08a";
            } else if (currentAgentState === "DICTATING") {
                primaryCol = "#ff0055"; glowCol = "#00f0ff"; eyeCol = "#ff3366";
            }

            const projFace = {};
            for (const [name, [x, y, z]] of Object.entries(faceVerts)) {
                let adjY = y;
                if (name === "lip_bot") adjY += mouthOpen * 0.75;
                else if (name === "chin_l" || name === "chin_r" || name === "chin_tip") adjY += mouthOpen * 0.95;
                else if (name === "jaw_l" || name === "jaw_r") adjY += mouthOpen * 0.45;
                projFace[name] = project3D(x, adjY, z, yaw, pitch, cx, cy);
            }

            // Outer Arc
            ctx.strokeStyle = primaryCol;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, 115, t3d * 0.8, t3d * 0.8 + 1.2);
            ctx.stroke();

            // Face Wireframe Edges
            for (const [v1, v2] of faceEdges) {
                const [x1, y1, z1] = projFace[v1];
                const [x2, y2, z2] = projFace[v2];
                ctx.strokeStyle = (z1 + z2 > -10) ? primaryCol : glowCol;
                ctx.lineWidth = (z1 + z2 > 15) ? 2 : 1;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }

            // Eyes Pupils
            const eyeL = [(projFace["e_l_in"][0] + projFace["e_l_out"][0]) / 2, (projFace["e_l_top"][1] + projFace["e_l_bot"][1]) / 2];
            const eyeR = [(projFace["e_r_in"][0] + projFace["e_r_out"][0]) / 2, (projFace["e_r_top"][1] + projFace["e_r_bot"][1]) / 2];
            ctx.fillStyle = eyeCol;
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(eyeL[0], eyeL[1], 4, 0, Math.PI * 2);
            ctx.fill(); ctx.stroke();
            ctx.beginPath();
            ctx.arc(eyeR[0], eyeR[1], 4, 0, Math.PI * 2);
            ctx.fill(); ctx.stroke();
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);'''

import re

portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    code = f.read()

pattern = r'const canvas = document\.getElementById\(\'visualizer-canvas\'\);.*?requestAnimationFrame\(renderVisualizer\);'
new_code, count = re.subn(pattern, f"const canvas = document.getElementById('visualizer-canvas');\n    const ctx = canvas.getContext('2d');\n\n{new_js_visualizer}", code, flags=re.DOTALL)
print(f"Replaced {count} occurrences in zen_web_portal.py")
if count > 0:
    with open(portal_path, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("zen_web_portal.py successfully updated!")

