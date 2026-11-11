import re

new_html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Z.E.N. // Command Center HUD</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #060911;
            --card-bg: rgba(14, 20, 32, 0.85);
            --card-border: rgba(0, 240, 255, 0.18);
            --cyan-glow: #00f0ff;
            --blue-accent: #0284c7;
            --purple-glow: #a855f7;
            --text-main: #f0f4fc;
            --text-dim: #8b9bb4;
            --danger: #ff0055;
            --success: #00ff88;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.09) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(168, 85, 247, 0.08) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Responsive Panoramic Grid */
        .portal-layout {
            width: 100%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding-bottom: 24px;
            transition: all 0.3s ease;
        }

        @media (min-width: 1024px) {
            .portal-layout {
                max-width: 1440px;
                display: grid;
                grid-template-columns: 310px 1fr 340px;
                gap: 20px;
                align-items: start;
            }
        }

        .side-col {
            display: none;
            flex-direction: column;
            gap: 16px;
        }

        @media (min-width: 1024px) {
            .side-col {
                display: flex;
            }
        }

        .center-col {
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
        }

        /* Generic Glass Card */
        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 16px;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 14px 18px;
            border-radius: 18px;
            backdrop-filter: blur(12px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--cyan-glow), var(--purple-glow));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 17px;
            color: #000;
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.45);
        }

        .brand-title {
            font-weight: 700;
            font-size: 18px;
            letter-spacing: 1px;
            color: #fff;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .fullscreen-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--card-border);
            color: #00f0ff;
            padding: 6px 12px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .fullscreen-btn:hover {
            background: rgba(0, 240, 255, 0.15);
            border-color: var(--cyan-glow);
        }

        .status-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 11px;
            border-radius: 20px;
            background: rgba(0, 255, 136, 0.1);
            color: var(--success);
            border: 1px solid rgba(0, 255, 136, 0.3);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Canvas AI Hologram Visualizer */
        .canvas-card {
            background: #080d1a;
            border: 1px solid var(--card-border);
            border-radius: 22px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 35px rgba(0,0,0,0.6);
        }

        #visualizer-canvas {
            width: 100%;
            max-width: 440px;
            height: 220px;
            display: block;
        }

        /* Voice Central Controller */
        .voice-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 22px;
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .mic-btn-wrapper {
            position: relative;
            margin: 12px 0;
        }

        .mic-glow {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 130px;
            height: 130px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0, 240, 255, 0.25) 0%, transparent 70%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .mic-btn-wrapper.recording .mic-glow {
            opacity: 1;
            animation: pulseGlow 1.2s infinite;
        }

        @keyframes pulseGlow {
            0% { transform: translate(-50%, -50%) scale(0.9); opacity: 0.5; }
            50% { transform: translate(-50%, -50%) scale(1.3); opacity: 0.9; }
            100% { transform: translate(-50%, -50%) scale(0.9); opacity: 0.5; }
        }

        .mic-btn {
            width: 88px;
            height: 88px;
            border-radius: 50%;
            background: linear-gradient(135deg, #121d2d, #1a273b);
            border: 2px solid var(--cyan-glow);
            color: var(--cyan-glow);
            font-size: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.25);
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            outline: none;
        }

        .mic-btn:active, .mic-btn-wrapper.recording .mic-btn {
            background: linear-gradient(135deg, var(--cyan-glow), var(--purple-glow));
            color: #000;
            border-color: #fff;
            transform: scale(0.94);
            box-shadow: 0 0 40px rgba(0, 240, 255, 0.8);
        }

        .voice-status-text {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dim);
            margin-top: 4px;
        }

        .voice-status-text.active {
            color: var(--cyan-glow);
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
        }

        /* Dialogue Box */
        .dialogue-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .card-header {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: var(--cyan-glow);
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .speech-bubble {
            padding: 12px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.45;
        }

        .user-bubble {
            background: rgba(0, 240, 255, 0.08);
            border-left: 3px solid var(--cyan-glow);
            color: #fff;
        }

        .zen-bubble {
            background: rgba(168, 85, 247, 0.1);
            border-left: 3px solid var(--purple-glow);
            color: #e0d4ff;
        }

        /* Controls Grid */
        .controls-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .action-btn {
            background: rgba(18, 26, 42, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.15);
            padding: 13px 12px;
            border-radius: 14px;
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            font-size: 13.5px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .action-btn:hover {
            border-color: var(--cyan-glow);
            background: rgba(0, 240, 255, 0.12);
        }

        .action-btn:active {
            transform: scale(0.96);
        }

        /* Typed Command Bar with Integrated Dictation Mic */
        .text-input-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(14, 20, 32, 0.95);
            border: 1px solid var(--card-border);
            padding: 6px 8px 6px 14px;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7);
        }

        .text-input-bar input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            outline: none;
        }

        .dictate-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.3);
            color: #00f0ff;
            padding: 9px 13px;
            border-radius: 10px;
            font-size: 15px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .dictate-btn.active {
            background: #ff0055;
            border-color: #ff0055;
            color: #fff;
            animation: pulse 1.2s infinite;
        }

        .send-btn {
            background: var(--blue-accent);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 700;
            font-size: 13.5px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .send-btn:hover {
            background: #0369a1;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.5);
        }

        /* Left Sidebar: Telemetry & Terminal Logs */
        .vitals-meter {
            margin-bottom: 12px;
        }

        .meter-label {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-dim);
            margin-bottom: 4px;
        }

        .meter-bar {
            width: 100%;
            height: 6px;
            background: #172238;
            border-radius: 4px;
            overflow: hidden;
        }

        .meter-fill {
            height: 100%;
            width: 0%;
            background: var(--cyan-glow);
            transition: width 0.5s ease;
        }

        .terminal-box {
            background: #050811;
            border: 1px solid #172238;
            border-radius: 12px;
            height: 340px;
            overflow-y: auto;
            padding: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            line-height: 1.6;
        }

        .log-entry {
            margin-bottom: 6px;
        }

        .log-time { color: #475569; }
        .log-user { color: #38bdf8; }
        .log-tool { color: #fbbf24; }
        .log-zen { color: #34d399; }
        .log-sys { color: #94a3b8; }
        .log-err { color: #f87171; }

        /* Right Sidebar: Chat History Cards & Inspector */
        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 380px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .chat-card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .chat-card:hover {
            border-color: var(--cyan-glow);
            background: #131d35;
        }

        .chat-card-top {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: #64748b;
            margin-bottom: 4px;
        }

        .chat-card-pill {
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 700;
            background: #1e1b4b;
            color: #c084fc;
        }

        .chat-card-pill.done {
            background: #064e3b;
            color: #34d399;
        }

        .chat-card-prompt {
            font-size: 12.5px;
            font-weight: 600;
            color: #e2e8f0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .inspector-box {
            background: #050811;
            border: 1px solid #172238;
            border-radius: 12px;
            padding: 12px;
            font-size: 12.5px;
            line-height: 1.5;
            color: #e2e8f0;
            max-height: 240px;
            overflow-y: auto;
        }
    </style>
</head>
<body>

<div class="portal-layout">
    <!-- LEFT SIDEBAR: Telemetry & Logs -->
    <div class="side-col">
        <div class="glass-card">
            <div class="card-header" style="margin-bottom: 12px;">
                <span>⚡ SYSTEM TELEMETRY</span>
                <span id="vitals-status" style="color: var(--success); font-size: 10px;">LIVE</span>
            </div>
            
            <div class="vitals-meter">
                <div class="meter-label">
                    <span>CPU LOAD</span>
                    <span id="cpu-val">0%</span>
                </div>
                <div class="meter-bar"><div class="meter-fill" id="cpu-fill"></div></div>
            </div>

            <div class="vitals-meter">
                <div class="meter-label">
                    <span>RAM USAGE</span>
                    <span id="ram-val">0%</span>
                </div>
                <div class="meter-bar"><div class="meter-fill" id="ram-fill" style="background: var(--purple-glow);"></div></div>
            </div>

            <div class="vitals-meter" style="margin-bottom: 6px;">
                <div class="meter-label">
                    <span>BATTERY</span>
                    <span id="batt-val">100% ⚡</span>
                </div>
            </div>

            <div style="font-size: 10.5px; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-top: 8px; border-top: 1px solid #1e293b; padding-top: 8px;">
                CORE: Groq LPU + Gemini 3.7<br>
                VOICE: hi-IN-MadhurNeural (+12%)
            </div>
        </div>

        <div class="glass-card" style="flex: 1;">
            <div class="card-header" style="margin-bottom: 8px;">
                <span>TERMINAL LOGS</span>
                <button onclick="clearTerminal()" style="background: transparent; border: none; color: #64748b; font-size: 10px; cursor: pointer;">Clear</button>
            </div>
            <div class="terminal-box" id="terminal-feed">
                <div class="log-entry"><span class="log-time">[System]</span> <span class="log-sys">ZEN Panoramic HUD Initialized.</span></div>
                <div class="log-entry"><span class="log-time">[System]</span> <span class="log-sys">Dual Engine Ready: Groq LPU + Gemini.</span></div>
            </div>
        </div>
    </div>

    <!-- CENTER COLUMN: Holographic Core & Command -->
    <div class="center-col">
        <!-- Top Header -->
        <div class="header">
            <div class="brand">
                <div class="brand-icon">⚡</div>
                <div>
                    <div class="brand-title">Z.E.N. // CORE</div>
                    <div style="font-size: 11px; color: var(--text-dim);">Autonomous Workstation Controller</div>
                </div>
            </div>
            <div class="header-actions">
                <button class="fullscreen-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
                <div class="status-badge" id="portal-status">
                    <div class="status-dot"></div>
                    <span id="portal-status-text">ONLINE</span>
                </div>
            </div>
        </div>

        <!-- Futuristic Holographic Visualizer Canvas -->
        <div class="canvas-card">
            <canvas id="visualizer-canvas" width="440" height="220"></canvas>
            <div id="visualizer-status-text" style="font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: var(--cyan-glow); margin-top: 6px;">
                NEURAL CORE ONLINE // STANDBY
            </div>
        </div>

        <!-- Dialogue Bubble -->
        <div class="dialogue-card">
            <div class="card-header">
                <span>Live Dialogue</span>
                <span id="audio-indicator" style="color: var(--success); font-size: 11px; cursor: pointer;" onclick="replayLastAudio()">🔊 Speaker Active</span>
            </div>
            <div class="speech-bubble user-bubble" id="user-transcript">
                Tap the mic below or type command to execute.
            </div>
            <div class="speech-bubble zen-bubble" id="zen-reply">
                <div id="zen-reply-text">Sir, ZEN Command Center online hai. Hukum kijiye?</div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 10px; color: var(--text-dim);">🔊 Natural Male Voice Active</span>
                    <button id="replay-btn" onclick="replayLastAudio()" style="background: rgba(0,240,255,0.15); border: 1px solid rgba(0,240,255,0.4); color: #00f0ff; padding: 4px 10px; border-radius: 8px; font-size: 11.5px; font-weight: 600; cursor: pointer;">🔊 Replay</button>
                </div>
            </div>
        </div>

        <!-- Interactive Typed Command Bar (With Dictation Mic inside before Send) -->
        <form class="text-input-bar" onsubmit="sendTextMessage(event)">
            <input type="text" id="cmd-input" placeholder="Type command in Roman Urdu / English, or use mic..." autocomplete="off" />
            <button type="button" class="dictate-btn" id="dictate-btn" onclick="toggleTextDictation()" title="Voice Dictation (English / Roman Urdu)">
                🎙️ <span id="dictate-label" style="font-size: 11px; font-weight: 700;">Mic</span>
            </button>
            <button type="submit" class="send-btn" id="send-btn">⚡ Send</button>
        </form>

        <!-- Quick Control Actions -->
        <div class="controls-grid">
            <button class="action-btn toggle-display-btn" id="display-toggle-btn" style="grid-column: span 2; background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(168, 85, 247, 0.15)); border-color: rgba(0, 240, 255, 0.4); font-size: 14.5px; padding: 14px;" onclick="toggleDisplayPower()">
                🖥️ Display: ON (Tap to Black)
            </button>
            <button class="action-btn" onclick="toggleScreen()">
                🖥️ View Screen
            </button>
            <button class="action-btn" onclick="triggerAction('close_apps')">
                🛑 Close Apps
            </button>
            <button class="action-btn" onclick="triggerAction('toggle_bt')">
                📶 Bluetooth
            </button>
            <button class="action-btn" onclick="triggerAction('check_bot')">
                🤖 Check Bot
            </button>
            <button class="action-btn" onclick="triggerAction('backtest_report')">
                📈 Backtest Report
            </button>
            <button class="action-btn" onclick="confirmShutdown()" style="color: #ff3366;">
                ⚡ Shutdown PC
            </button>
        </div>

        <!-- Desktop Screen Modal -->
        <div id="screen-container" style="display: none; width: 100%; flex-direction: column; gap: 8px; background: rgba(16, 22, 34, 0.9); border: 1px solid var(--card-border); padding: 12px; border-radius: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--cyan-glow); font-family: 'JetBrains Mono', monospace;">
                <span>🖥️ Live Desktop Feed</span>
                <div style="display: flex; gap: 8px;">
                    <button onclick="refreshScreen()" style="background: rgba(0,240,255,0.15); color: #00f0ff; border: 1px solid rgba(0,240,255,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">🔄 Refresh</button>
                    <button onclick="toggleScreen()" style="background: rgba(255,0,85,0.15); color: #ff0055; border: 1px solid rgba(255,0,85,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">✕ Close</button>
                </div>
            </div>
            <img id="desktop-screen-img" alt="Desktop Screen" style="display: block; width: 100%; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);" />
        </div>
    </div>

    <!-- RIGHT SIDEBAR: Chat History & Response Inspector -->
    <div class="side-col">
        <div class="glass-card" style="flex: 1;">
            <div class="card-header" style="margin-bottom: 4px;">
                <span>💬 CHATS & ACTIONS</span>
                <span style="font-size: 10px; color: #64748b;" id="chat-count">0 items</span>
            </div>
            <div style="font-size: 10.5px; color: var(--text-dim); margin-bottom: 10px;">Click card to inspect full response</div>
            
            <div class="chat-list" id="chat-cards-list">
                <!-- Chat cards dynamically appended here -->
            </div>
        </div>

        <div class="glass-card">
            <div class="card-header" style="margin-bottom: 8px;">
                <span>RESPONSE INSPECTOR</span>
            </div>
            <div class="inspector-box" id="inspector-content">
                Select any card above to view execution details and final response.
            </div>
        </div>
    </div>
</div>

<!-- Shutdown Modal -->
<div id="shutdown-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 99999; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); align-items: center; justify-content: center; padding: 20px;">
    <div style="background: #0e1422; border: 1px solid rgba(255, 0, 85, 0.5); border-radius: 20px; padding: 24px; max-width: 360px; width: 100%; box-shadow: 0 0 35px rgba(255, 0, 85, 0.35); text-align: center; display: flex; flex-direction: column; gap: 14px;">
        <div style="font-size: 40px; filter: drop-shadow(0 0 10px rgba(255, 0, 85, 0.6));">⚠️</div>
        <div style="font-family: 'Outfit', sans-serif; font-size: 18px; font-weight: 700; color: #fff;">Confirm PC Shutdown?</div>
        <div style="font-size: 13.5px; color: var(--text-dim); line-height: 1.45;">Sir, kya aap sach mein PC shutdown karna chahte hain? Tamam running tasks close ho jayenge.</div>
        <div style="display: flex; gap: 10px; margin-top: 8px;">
            <button onclick="closeShutdownModal()" style="flex: 1; background: rgba(255,255,255,0.08); border: 1px solid var(--card-border); color: #fff; padding: 12px; border-radius: 12px; font-weight: 600; font-size: 14px; cursor: pointer;">Cancel</button>
            <button onclick="executeShutdown()" style="flex: 1; background: linear-gradient(135deg, #ff0055, #ff3366); border: none; color: #fff; padding: 12px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 0 18px rgba(255, 0, 85, 0.5);">Yes, Shutdown</button>
        </div>
    </div>
</div>

<audio id="tts-audio" playsinline preload="auto"></audio>

<script>
    // State
    let isRecording = false;
    let isDictating = false;
    let dictationRecorder = null;
    let dictationChunks = [];
    let lastAudioBase64 = null;
    let lastAudioBlobUrl = null;
    let chatCardsData = [];
    let currentAgentState = "IDLE";

    const userTranscript = document.getElementById('user-transcript');
    const zenReplyText = document.getElementById('zen-reply-text');
    const ttsAudio = document.getElementById('tts-audio');
    const audioIndicator = document.getElementById('audio-indicator');
    const cmdInput = document.getElementById('cmd-input');
    const dictateBtn = document.getElementById('dictate-btn');
    const dictateLabel = document.getElementById('dictate-label');
    const terminalFeed = document.getElementById('terminal-feed');
    const chatCardsList = document.getElementById('chat-cards-list');
    const inspectorContent = document.getElementById('inspector-content');
    const visualizerStatus = document.getElementById('visualizer-status-text');

    // Canvas Hologram Setup
    const canvas = document.getElementById('visualizer-canvas');
    const ctx = canvas.getContext('2d');
    let animAngle = 0.0;
    let innerAngle = 0.0;
    let pulseVal = 0.0;

    function renderVisualizer() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        animAngle += 0.035;
        innerAngle -= 0.045;
        pulseVal += 0.09;

        let primaryCol = "#00f0ff";
        let secCol = "#0284c7";
        let waveAmp = 14;

        if (currentAgentState === "LISTENING") {
            primaryCol = "#fbbf24"; secCol = "#f59e0b"; waveAmp = 32;
        } else if (currentAgentState === "THINKING") {
            primaryCol = "#c084fc"; secCol = "#818cf8"; waveAmp = 36;
        } else if (currentAgentState === "SPEAKING") {
            primaryCol = "#00f0ff"; secCol = "#38bdf8"; waveAmp = 46;
        } else if (currentAgentState === "DICTATING") {
            primaryCol = "#ff0055"; secCol = "#00f0ff"; waveAmp = 38;
        }

        // Radar ring
        const rOuter = 82 + Math.sin(pulseVal * 0.4) * 4;
        ctx.beginPath();
        ctx.arc(cx, cy, rOuter, 0, Math.PI * 2);
        ctx.strokeStyle = "#1e293b";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Ticks
        for (let i = 0; i < 20; i++) {
            const theta = animAngle + (i * Math.PI * 2 / 20);
            const x1 = cx + (rOuter - 6) * Math.cos(theta);
            const y1 = cy + (rOuter - 6) * Math.sin(theta);
            const x2 = cx + (rOuter + 6) * Math.cos(theta);
            const y2 = cy + (rOuter + 6) * Math.sin(theta);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = (i % 4 === 0) ? primaryCol : "#334155";
            ctx.lineWidth = (i % 4 === 0) ? 2 : 1;
            ctx.stroke();
        }

        // Outer arc
        ctx.beginPath();
        ctx.arc(cx, cy, rOuter + 4, animAngle, animAngle + 1.2);
        ctx.strokeStyle = primaryCol;
        ctx.lineWidth = 2.5;
        ctx.stroke();

        // Inner waveform
        const rInner = 52;
        for (let b = 0; b < 28; b++) {
            const theta = innerAngle + (b * Math.PI * 2 / 28);
            let bH = Math.sin(pulseVal + b * 0.6) * waveAmp;
            if (bH < 0) bH = Math.abs(bH) * 0.35;
            const bx1 = cx + (rInner - 2) * Math.cos(theta);
            const by1 = cy + (rInner - 2) * Math.sin(theta);
            const bx2 = cx + (rInner + bH + 2) * Math.cos(theta);
            const by2 = cy + (rInner + bH + 2) * Math.sin(theta);
            ctx.beginPath();
            ctx.moveTo(bx1, by1);
            ctx.lineTo(bx2, by2);
            ctx.strokeStyle = primaryCol;
            ctx.lineWidth = 1.8;
            ctx.stroke();
        }

        // Core Glowing Orb
        const coreR = 26 + Math.sin(pulseVal) * 3;
        ctx.beginPath();
        ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
        ctx.fillStyle = "#0b1728";
        ctx.fill();
        ctx.strokeStyle = primaryCol;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Center Symbol
        ctx.font = "bold 15px 'JetBrains Mono', monospace";
        ctx.fillStyle = primaryCol;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("⚡", cx, cy);

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);

    function setAgentState(state) {
        currentAgentState = state.toUpperCase();
        const map = {
            "IDLE": "NEURAL CORE ONLINE // STANDBY",
            "LISTENING": "MIC ACTIVE // LISTENING...",
            "THINKING": "NEURAL INFERENCE // EXECUTING TOOLS...",
            "SPEAKING": "SYNTHESIZING SPEECH // TRANSMITTING...",
            "DICTATING": "VOICE DICTATION // SPEAK NOW (EN/ROMAN URDU)..."
        };
        visualizerStatus.textContent = map[currentAgentState] || ("STATE: " + currentAgentState);
    }

    // Fullscreen Toggle
    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
        }
    }

    // Append Terminal Log
    function addTerminalLog(sender, text, tag) {
        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = "log-entry";
        entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${tag}">[${sender}]:</span> ${text}`;
        terminalFeed.appendChild(entry);
        terminalFeed.scrollTop = terminalFeed.scrollHeight;
    }

    function clearTerminal() {
        terminalFeed.innerHTML = "";
    }

    // Chat History Cards
    function addChatCard(prompt) {
        const id = chatCardsData.length;
        const time = new Date().toLocaleTimeString();
        const cardObj = { id, time, prompt, response: "Processing...", status: "In Progress" };
        chatCardsData.push(cardObj);

        const card = document.createElement('div');
        card.className = "chat-card";
        card.id = `chat-card-${id}`;
        card.onclick = () => inspectChat(id);
        card.innerHTML = `
            <div class="chat-card-top">
                <span>[${time}]</span>
                <span class="chat-card-pill" id="card-pill-${id}">⚡ Running</span>
            </div>
            <div class="chat-card-prompt">${prompt}</div>
        `;
        chatCardsList.prepend(card);
        document.getElementById('chat-count').textContent = chatCardsData.length + " items";
        return id;
    }

    function updateChatCard(id, response) {
        if (chatCardsData[id]) {
            chatCardsData[id].response = response;
            chatCardsData[id].status = "Completed";
            const pill = document.getElementById(`card-pill-${id}`);
            if (pill) {
                pill.textContent = "✓ Done";
                pill.className = "chat-card-pill done";
            }
            inspectChat(id);
        }
    }

    function inspectChat(id) {
        if (chatCardsData[id]) {
            const item = chatCardsData[id];
            inspectorContent.innerHTML = `
                <div style="font-size: 11px; color: var(--cyan-glow); font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">[CARD #${id+1} // ${item.time}]</div>
                <div style="color: #94a3b8; font-size: 11.5px; margin-bottom: 4px;"><strong>PROMPT:</strong></div>
                <div style="color: #fff; margin-bottom: 10px; font-weight: 600;">${item.prompt}</div>
                <div style="color: #94a3b8; font-size: 11.5px; margin-bottom: 4px;"><strong>ZEN REPLY:</strong></div>
                <div style="color: #34d399;">${item.response}</div>
            `;
        }
    }

    // Audio Playback
    function unlockIOSAudio() {
        if (ttsAudio) {
            ttsAudio.play().then(() => ttsAudio.pause()).catch(() => {});
        }
    }
    document.addEventListener('touchstart', unlockIOSAudio, { passive: true });
    document.addEventListener('click', unlockIOSAudio, { passive: true });

    function playTTSAudio(base64Audio) {
        if (!base64Audio) return;
        lastAudioBase64 = base64Audio;
        try {
            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
            if (lastAudioBlobUrl) URL.revokeObjectURL(lastAudioBlobUrl);
            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            lastAudioBlobUrl = URL.createObjectURL(blob);
            ttsAudio.pause();
            ttsAudio.src = lastAudioBlobUrl;
            setAgentState("SPEAKING");
            ttsAudio.play().then(() => {
                audioIndicator.textContent = "🔊 Playing Audio...";
                ttsAudio.onended = () => {
                    audioIndicator.textContent = "🔊 Speaker Active";
                    setAgentState("IDLE");
                };
            }).catch(() => {
                setAgentState("IDLE");
            });
        } catch (e) {
            console.error("Audio playback error:", e);
        }
    }

    function replayLastAudio() {
        if (lastAudioBase64) playTTSAudio(lastAudioBase64);
    }

    // Live Voice Dictation in Input Bar
    async function toggleTextDictation() {
        unlockIOSAudio();
        if (!isDictating) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                dictationChunks = [];
                dictationRecorder = new MediaRecorder(stream);
                dictationRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) dictationChunks.push(e.data);
                };
                dictationRecorder.onstop = async () => {
                    const audioBlob = new Blob(dictationChunks, { type: 'audio/wav' });
                    dictateLabel.textContent = "Transcribing...";
                    setAgentState("THINKING");
                    const formData = new FormData();
                    formData.append("audio", audioBlob, "dictation.wav");
                    try {
                        const res = await fetch("/api/dictate_stt", { method: "POST", body: formData });
                        const data = await res.json();
                        if (data.status === "success" && data.text) {
                            const curr = cmdInput.value.trim();
                            cmdInput.value = curr ? `${curr} ${data.text}` : data.text;
                            addTerminalLog("Dictation", `Recognized: "${data.text}"`, "tool");
                        }
                    } catch (err) {
                        console.error("Dictation error:", err);
                    }
                    dictateLabel.textContent = "Mic";
                    dictateBtn.classList.remove('active');
                    isDictating = false;
                    setAgentState("IDLE");
                    stream.getTracks().forEach(t => t.stop());
                };

                dictationRecorder.start();
                isDictating = true;
                dictateBtn.classList.add('active');
                dictateLabel.textContent = "Stop";
                setAgentState("DICTATING");
                addTerminalLog("Dictation", "Listening... Speak in English or Urdu", "sys");
            } catch (err) {
                alert("Microphone permission required: " + err);
            }
        } else {
            if (dictationRecorder && isDictating) {
                dictationRecorder.stop();
            }
        }
    }

    // Send Text Message
    async function sendTextMessage(e) {
        e.preventDefault();
        unlockIOSAudio();
        const text = cmdInput.value.trim();
        if (!text) return;
        cmdInput.value = "";

        const cardId = addChatCard(text);
        addTerminalLog("You", text, "user");
        userTranscript.textContent = "⌨️ " + text;
        zenReplyText.textContent = "ZEN executing...";
        setAgentState("THINKING");

        try {
            const res = await fetch("/api/text_command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
            const data = await res.json();
            if (data.status === "success") {
                zenReplyText.textContent = "⚡ " + data.reply_text;
                addTerminalLog("ZEN", data.reply_text, "zen");
                updateChatCard(cardId, data.reply_text);
                if (data.audio_base64) {
                    playTTSAudio(data.audio_base64);
                } else {
                    setAgentState("IDLE");
                }
            } else {
                zenReplyText.textContent = "❌ " + data.reply_text;
                addTerminalLog("Error", data.reply_text, "err");
                updateChatCard(cardId, data.reply_text);
                setAgentState("IDLE");
            }
        } catch (err) {
            zenReplyText.textContent = "Error: " + err;
            addTerminalLog("Error", String(err), "err");
            updateChatCard(cardId, String(err));
            setAgentState("IDLE");
        }
    }

    // Quick Actions
    async function triggerAction(actionName) {
        unlockIOSAudio();
        const cardId = addChatCard(`Action: ${actionName}`);
        addTerminalLog("Action", `Triggering ${actionName}`, "tool");
        zenReplyText.textContent = "Executing " + actionName + "...";
        setAgentState("THINKING");
        try {
            const res = await fetch("/api/quick_action", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: actionName })
            });
            const data = await res.json();
            zenReplyText.textContent = "⚡ " + data.message;
            addTerminalLog("ZEN", data.message, "zen");
            updateChatCard(cardId, data.message);
            if (data.audio_base64) {
                playTTSAudio(data.audio_base64);
            } else {
                setAgentState("IDLE");
            }
        } catch (err) {
            zenReplyText.textContent = "Error: " + err;
            setAgentState("IDLE");
        }
    }

    let isDisplayOn = true;
    async function toggleDisplayPower() {
        unlockIOSAudio();
        const btn = document.getElementById('display-toggle-btn');
        isDisplayOn = !isDisplayOn;
        if (!isDisplayOn) {
            btn.innerHTML = '🌑 Display: BLACK (Tap to Wake)';
            triggerAction('screen_off');
        } else {
            btn.innerHTML = '🖥️ Display: ON (Tap to Black)';
            triggerAction('wake_screen');
        }
    }

    function toggleScreen() {
        const sc = document.getElementById('screen-container');
        if (sc.style.display === 'none' || !sc.style.display) {
            sc.style.display = 'flex';
            refreshScreen();
        } else {
            sc.style.display = 'none';
        }
    }

    function refreshScreen() {
        const img = document.getElementById('desktop-screen-img');
        img.src = '/api/screen_preview?' + new Date().getTime();
    }

    function confirmShutdown() {
        document.getElementById('shutdown-modal').style.display = 'flex';
    }
    function closeShutdownModal() {
        document.getElementById('shutdown-modal').style.display = 'none';
    }
    async function executeShutdown() {
        closeShutdownModal();
        triggerAction('shutdown');
    }

    // Telemetry Poller
    async function pollVitals() {
        try {
            const res = await fetch('/api/system_vitals');
            const data = await res.json();
            if (data.status === 'success') {
                document.getElementById('cpu-val').textContent = Math.round(data.cpu) + '%';
                document.getElementById('cpu-fill').style.width = Math.min(100, data.cpu) + '%';
                document.getElementById('ram-val').textContent = Math.round(data.ram) + '%';
                document.getElementById('ram-fill').style.width = Math.min(100, data.ram) + '%';
                const plugIcon = data.plugged ? '⚡' : '🔋';
                document.getElementById('batt-val').textContent = data.battery + '% ' + plugIcon;
            }
        } catch (e) {}
        setTimeout(pollVitals, 3000);
    }
    pollVitals();
</script>
</body>
</html>
'''

# Read zen_web_portal.py
portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace mobile_portal_ui function
pattern = r'@app\.get\("/", response_class=HTMLResponse\)\s*async def mobile_portal_ui\(\):.*?(?=def start_cloudflare_tunnel)'
replacement = f'''@app.get("/", response_class=HTMLResponse)
async def mobile_portal_ui():
    """Returns stunning Cyberpunk Panoramic Web Portal for Desktop & Mobile."""
    html_content = """{new_html_content}"""
    return HTMLResponse(content=html_content)

'''

new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
print(f"Replaced {count} occurrences.")
if count == 1:
    with open(portal_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("zen_web_portal.py successfully updated!")
else:
    print("Pattern match failed!")

