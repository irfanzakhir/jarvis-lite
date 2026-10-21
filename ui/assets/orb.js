// Siri-Style Rotating Glowing Orb Canvas Renderer

const canvas = document.getElementById("orbCanvas");
const ctx = canvas.getContext("2d");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const speechBubble = document.getElementById("speechBubble");
const commandInput = document.getElementById("commandInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const muteBtn = document.getElementById("muteBtn");
const muteHeaderBtn = document.getElementById("muteHeaderBtn");
const toolCard = document.getElementById("toolCard");
const toolTitle = document.getElementById("toolTitle");
const toolDetail = document.getElementById("toolDetail");
const confirmActions = document.getElementById("confirmActions");
const btnApprove = document.getElementById("btnApprove");
const btnCancel = document.getElementById("btnCancel");
const hudToggleBtn = document.getElementById("hudToggleBtn");
const hudPanel = document.getElementById("hudPanel");
const closeBtn = document.getElementById("closeBtn");
const orbHalo = document.getElementById("orbHalo");

let currentState = "idle"; // idle, listening, thinking, speaking, executing
let time = 0;
let hudVisible = true;

// Orb Rendering Configuration
const ORB_RADIUS = 68;
const CENTER_X = canvas.width / 2;
const CENTER_Y = canvas.height / 2;

// Dynamic State Color Palettes & Speeds
const STATE_PROFILES = {
  idle: {
    speed: 0.015,
    hueOffset: 0,
    colors: ["#38bdf8", "#818cf8", "#c084fc", "#f472b6"],
    dotColor: "#10b981",
    status: "Ready",
    halo: "radial-gradient(circle, rgba(168, 85, 247, 0.3) 0%, rgba(59, 130, 246, 0.15) 60%, transparent 80%)"
  },
  listening: {
    speed: 0.04,
    hueOffset: 40,
    colors: ["#06b6d4", "#3b82f6", "#60a5fa", "#38bdf8"],
    dotColor: "#06b6d4",
    status: "Listening...",
    halo: "radial-gradient(circle, rgba(6, 182, 212, 0.5) 0%, rgba(59, 130, 246, 0.3) 70%, transparent 90%)"
  },
  thinking: {
    speed: 0.07,
    hueOffset: 120,
    colors: ["#ec4899", "#8b5cf6", "#a855f7", "#6366f1"],
    dotColor: "#a855f7",
    status: "Thinking...",
    halo: "radial-gradient(circle, rgba(236, 72, 153, 0.45) 0%, rgba(139, 92, 246, 0.3) 65%, transparent 85%)"
  },
  speaking: {
    speed: 0.035,
    hueOffset: 80,
    colors: ["#fbbf24", "#f43f5e", "#a855f7", "#38bdf8"],
    dotColor: "#fbbf24",
    status: "Speaking...",
    halo: "radial-gradient(circle, rgba(251, 191, 36, 0.4) 0%, rgba(244, 63, 94, 0.25) 65%, transparent 85%)"
  },
  executing: {
    speed: 0.06,
    hueOffset: 200,
    colors: ["#10b981", "#06b6d4", "#3b82f6", "#2dd4bf"],
    dotColor: "#10b981",
    status: "Executing...",
    halo: "radial-gradient(circle, rgba(16, 185, 129, 0.4) 0%, rgba(6, 182, 212, 0.25) 65%, transparent 85%)"
  }
};

// Render Loop for Siri-style Multi-ring Chromatic Orb
function drawOrb() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const profile = STATE_PROFILES[currentState] || STATE_PROFILES.idle;
  time += profile.speed;

  // 1. Core Glowing Base Sphere
  const coreGrad = ctx.createRadialGradient(
    CENTER_X, CENTER_Y, 10,
    CENTER_X, CENTER_Y, ORB_RADIUS
  );
  coreGrad.addColorStop(0, "rgba(255, 255, 255, 0.9)");
  coreGrad.addColorStop(0.3, profile.colors[0]);
  coreGrad.addColorStop(0.7, profile.colors[1]);
  coreGrad.addColorStop(1, "rgba(15, 23, 42, 0)");

  ctx.save();
  ctx.fillStyle = coreGrad;
  ctx.beginPath();
  ctx.arc(CENTER_X, CENTER_Y, ORB_RADIUS * 0.85, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // 2. Rotating 3D Chromatic Energy Rings (Siri Wave Simulation)
  const ringCount = 5;
  for (let i = 0; i < ringCount; i++) {
    const angleOffset = (i * Math.PI) / ringCount;
    const waveAmp = (currentState === "speaking" || currentState === "listening") ? 8 : 4;
    const currentRadius = ORB_RADIUS + Math.sin(time * 3 + i) * waveAmp;

    ctx.save();
    ctx.translate(CENTER_X, CENTER_Y);
    ctx.rotate(time * (1 + i * 0.2) + angleOffset);

    // Dynamic 3D tilt ellipse
    const scaleY = Math.cos(time * 1.5 + angleOffset * 2) * 0.65;
    ctx.scale(1, Math.max(0.2, Math.abs(scaleY)));

    ctx.beginPath();
    ctx.arc(0, 0, currentRadius, 0, Math.PI * 2);

    const strokeGrad = ctx.createLinearGradient(-currentRadius, 0, currentRadius, 0);
    strokeGrad.addColorStop(0, profile.colors[i % profile.colors.length]);
    strokeGrad.addColorStop(0.5, "rgba(255, 255, 255, 0.8)");
    strokeGrad.addColorStop(1, profile.colors[(i + 1) % profile.colors.length]);

    ctx.strokeStyle = strokeGrad;
    ctx.lineWidth = (currentState === "speaking" || currentState === "listening") ? 3.5 : 2.2;
    ctx.shadowColor = profile.colors[i % profile.colors.length];
    ctx.shadowBlur = 14;
    ctx.stroke();
    ctx.restore();
  }

  // 3. Orbiting Data Particles
  const particleCount = currentState === "thinking" || currentState === "executing" ? 16 : 8;
  for (let j = 0; j < particleCount; j++) {
    const pAngle = time * 2.5 + (j * (Math.PI * 2)) / particleCount;
    const pDist = ORB_RADIUS * 1.05 + Math.sin(time * 4 + j) * 8;
    const px = CENTER_X + Math.cos(pAngle) * pDist;
    const py = CENTER_Y + Math.sin(pAngle) * (pDist * 0.45);

    ctx.save();
    ctx.fillStyle = "#ffffff";
    ctx.shadowColor = profile.colors[j % profile.colors.length];
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(px, py, 2.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  requestAnimationFrame(drawOrb);
}

// State Switcher
function setState(newState) {
  if (STATE_PROFILES[newState]) {
    currentState = newState;
    const prof = STATE_PROFILES[newState];
    statusDot.style.background = prof.dotColor;
    statusDot.style.boxShadow = `0 0 10px ${prof.dotColor}`;
    statusText.textContent = prof.status;
    orbHalo.style.background = prof.halo;
    if (newState === "listening") {
      if (!hudVisible) {
        hudVisible = true;
        if (hudPanel) hudPanel.style.display = "flex";
        if (hudToggleBtn) hudToggleBtn.textContent = "▼";
      }
      micBtn.classList.add("recording");
      if (muteBtn) muteBtn.classList.add("active-listening");
      if (muteHeaderBtn) muteHeaderBtn.classList.add("active-listening");
    } else {
      micBtn.classList.remove("recording");
      if (muteBtn) muteBtn.classList.remove("active-listening");
      if (muteHeaderBtn) muteHeaderBtn.classList.remove("active-listening");
    }
  }
}

// Mute / Cancel Listening Function
function muteListening() {
  if (currentState === "listening") {
    setState("idle");
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.stop_listening();
    }
    speechBubble.textContent = "Listening muted. Type your command and press Enter.";
  } else {
    speechBubble.textContent = "Microphone muted. Type your command below.";
  }
  if (commandInput) {
    commandInput.focus();
  }
}

// User Action Handlers
function submitQuery() {
  if (currentState === "listening") {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.stop_listening();
    }
    setState("idle");
  }
  const query = commandInput.value.trim();
  if (!query) return;

  commandInput.value = "";
  speechBubble.textContent = `You: "${query}"`;
  setState("thinking");

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.submit_query(query).then((response) => {
      handleAssistantResponse(response);
    }).catch((err) => {
      speechBubble.textContent = `Error: ${err}`;
      setState("idle");
    });
  } else {
    // Demo fallback for browser testing
    setTimeout(() => {
      speechBubble.textContent = `Assistant: "Executed: ${query}"`;
      setState("idle");
    }, 1200);
  }
}

function handleAssistantResponse(resp) {
  if (!resp) return;

  // Ignore intermediate start/status acknowledgments
  if (resp.status === "listening_started" || resp.status === "already_listening") {
    return;
  }

  if (resp.reply) {
    speechBubble.textContent = resp.reply;
  }

  if (resp.action === "execute_powershell" || (resp.tool_calls && resp.tool_calls.length > 0)) {
    const call = resp.tool_calls ? resp.tool_calls[0] : null;
    const detail = call ? `${call.name}: ${JSON.stringify(call.arguments)}` : (resp.params?.cmd || resp.action);
    toolTitle.textContent = "⚡ PowerShell / System Action";
    toolDetail.textContent = detail;
    toolCard.style.display = "block";
    confirmActions.style.display = resp.needs_confirmation ? "flex" : "none";
  } else {
    toolCard.style.display = "none";
  }

  if (currentState !== "speaking") {
    setState("idle");
  }
}

function toggleMic() {
  if (currentState === "listening") {
    muteListening();
  } else {
    setState("listening");
    speechBubble.textContent = "Listening to your voice... (Click 🔇 to mute or type)";
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.start_listening().then((response) => {
        if (response && response.reply) {
          handleAssistantResponse(response);
        }
      }).catch((err) => {
        speechBubble.textContent = `Mic error: ${err}`;
        setState("idle");
      });
    }
  }
}

// Event Listeners
sendBtn.addEventListener("click", () => {
  if (currentState === "listening") {
    muteListening();
  }
  submitQuery();
});

if (commandInput) {
  commandInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      if (currentState === "listening") {
        muteListening();
      }
      submitQuery();
    }
  });

  // Focus or click inside the input area immediately cancels listening and enables typing
  commandInput.addEventListener("focus", () => {
    if (currentState === "listening") {
      muteListening();
    }
  });

  commandInput.addEventListener("click", () => {
    if (currentState === "listening") {
      muteListening();
    }
  });

  commandInput.addEventListener("input", () => {
    if (currentState === "listening") {
      muteListening();
    }
  });
}

micBtn.addEventListener("click", toggleMic);
document.getElementById("orbWrapper").addEventListener("click", toggleMic);

if (muteBtn) {
  muteBtn.addEventListener("click", muteListening);
}

if (muteHeaderBtn) {
  muteHeaderBtn.addEventListener("click", muteListening);
}

hudToggleBtn.addEventListener("click", () => {
  hudVisible = !hudVisible;
  hudPanel.style.display = hudVisible ? "flex" : "none";
  hudToggleBtn.textContent = hudVisible ? "▼" : "▲";
});

closeBtn.addEventListener("click", () => {
  if (currentState === "listening") {
    muteListening();
  }
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.hide_window();
  }
});

// Escape key cancels listening and focuses input box
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (currentState === "listening") {
      muteListening();
    }
  }
});

btnApprove.addEventListener("click", () => {
  toolCard.style.display = "none";
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.confirm_action(true).then((res) => {
      if (res && res.reply) {
        speechBubble.textContent = res.reply;
      }
    });
  }
});

btnCancel.addEventListener("click", () => {
  toolCard.style.display = "none";
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.confirm_action(false).then((res) => {
      if (res && res.reply) {
        speechBubble.textContent = res.reply;
      }
    });
  }
});

// Exposed bridge functions for Python
window.setAssistantState = function(state) {
  setState(state);
};

window.setSpeechBubble = function(text) {
  speechBubble.textContent = text;
};

window.onAssistantResponse = function(resp) {
  handleAssistantResponse(resp);
};
window.handleAssistantResponse = window.onAssistantResponse;

// Smooth Desktop Window Dragging via pywebview bridge
let isDraggingWindow = false;
let dragStartX = 0;
let dragStartY = 0;
let dragRafId = null;

const dragBarElem = document.getElementById("dragBar");
if (dragBarElem) {
  dragBarElem.addEventListener("mousedown", (e) => {
    if (e.target.closest(".no-drag") || e.target.tagName === "BUTTON") return;
    isDraggingWindow = true;
    dragStartX = e.screenX;
    dragStartY = e.screenY;
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDraggingWindow) return;
    const deltaX = e.screenX - dragStartX;
    const deltaY = e.screenY - dragStartY;
    dragStartX = e.screenX;
    dragStartY = e.screenY;

    if (deltaX === 0 && deltaY === 0) return;

    if (!dragRafId) {
      dragRafId = requestAnimationFrame(() => {
        dragRafId = null;
        if (window.pywebview && window.pywebview.api && window.pywebview.api.move_window) {
          window.pywebview.api.move_window(deltaX, deltaY);
        }
      });
    }
  });

  window.addEventListener("mouseup", () => {
    isDraggingWindow = false;
  });
}

// Start Orb Animation
drawOrb();
