const CAM_W = 640;
const CAM_H = 480;
const SIM_W = 1920;
const SIM_H = 1080;
const ROBOT_SPEED = 0.15;
const WORLD_RADIUS = 8.0;
const GESTURE_STABLE_FRAMES = 3;
const TURN_SPEED = 10.0;
const PICKUP_RANGE = 1.5;
const CLICK_COOLDOWN = 0.5;
const TOOLBOX_CATEGORIES = ["Chassis", "Wheels (WASD)", "Lidar", "Camera (View)", "Arm (SPACE)"];
const TOOLBOX_PARTS = {
  "Chassis": ["None", "Standard", "Tank", "Humanoid", "Spider"],
  "Wheels (WASD)": ["None", "Standard", "Treads", "Legs"],
  "Lidar": ["Off", "On"],
  "Camera (View)": ["None", "Standard", "Wide-Angle", "Thermal"],
  "Arm (SPACE)": ["None", "Retracted", "Extended"]
};
const TOOLBOX_COLORS = [
  [100, 140, 50],
  [50, 110, 220],
  [50, 50, 200],
  [230, 110, 60],
  [220, 50, 150]
];
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17]
];
const SHAPE_TYPES = ["circle", "square", "triangle"];
const OBJECT_COLORS = [
  [0, 200, 0], [0, 120, 255], [255, 100, 100], [200, 0, 200],
  [0, 255, 255], [50, 200, 255], [255, 200, 0], [100, 255, 100],
  [180, 50, 255], [255, 150, 50]
];
const HUMAN_COLORS = [
  [200, 200, 200],
  [180, 160, 255],
  [150, 220, 255],
  [200, 255, 180]
];
const MEDIAPIPE_SOURCES = [
  {
    moduleUrl: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs",
    wasmRoot: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm"
  },
  {
    moduleUrl: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.mjs",
    wasmRoot: "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
  },
  {
    moduleUrl: "https://unpkg.com/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs",
    wasmRoot: "https://unpkg.com/@mediapipe/tasks-vision@0.10.21/wasm"
  }
];
const HAND_LANDMARKER_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task";

const canvas = document.getElementById("simCanvas");
const ctx = canvas.getContext("2d");
const video = document.getElementById("cameraVideo");
const detectionCanvas = document.createElement("canvas");
const detectionCtx = detectionCanvas.getContext("2d");
const tempRobotCanvas = document.createElement("canvas");
const tempRobotCtx = tempRobotCanvas.getContext("2d");
const robotViewCanvas = document.createElement("canvas");
const robotViewCtx = robotViewCanvas.getContext("2d");

detectionCanvas.width = CAM_W;
detectionCanvas.height = CAM_H;
tempRobotCanvas.width = 250;
tempRobotCanvas.height = 250;
robotViewCanvas.width = 320;
robotViewCanvas.height = 240;

let handLandmarker = null;
let mediaStream = null;
let lastVideoTime = -1;
let lastDetectionResults = null;
let running = false;
let visionModule = null;
let activeWasmRoot = "";
let bootTitle = "INITIALIZING";
let bootDetail = "Loading hand tracking";
let bootError = false;
let frameSeconds = 0;
let controlMode = "gesture";
let modeBannerTitle = "GESTURE MODE";
let modeBannerDetail = "Allow camera access to control the robot with hand tracking";
let cameraAvailable = false;
let handTrackingAvailable = false;
let manualPresetApplied = false;
const directOpenMode = window.location.protocol === "file:";
const manualKeys = {
  KeyW: false,
  KeyA: false,
  KeyS: false,
  KeyD: false
};

let robotX = 0.0;
let robotZ = 0.0;
let robotAngle = 0.0;
let targetAngle = 0.0;
let robotState = "IDLE";
let currentGesture = "NONE";
let stableGesture = "NONE";
const gestureHistory = [];

let actionGesture = "NONE";
let stableActionGesture = "NONE";
const actionGestureHistory = [];
let robotFrozen = false;
let prevActionFist = false;

let heldObject = null;
let heldObjectIndex = null;

const selectedParts = Object.fromEntries(TOOLBOX_CATEGORIES.map((cat) => [cat, 0]));

let lastClickTime = 0.0;
let lastHoveredCat = null;
let cursorX = -100;
let cursorY = -100;
let pinching = false;
let showCursor = false;

const staticObjects = [];
const wanderingHumans = [];
const colorCache = new Map();
const rng = mulberry32(42);

for (let i = 0; i < 50; i += 1) {
  staticObjects.push({
    x: randFloat(-WORLD_RADIUS * 0.95, WORLD_RADIUS * 0.95),
    z: randFloat(-WORLD_RADIUS * 0.95, WORLD_RADIUS * 0.95),
    color: choose(OBJECT_COLORS),
    shape: choose(SHAPE_TYPES),
    size: randInt(6, 14)
  });
}

for (let i = 0; i < 12; i += 1) {
  wanderingHumans.push({
    x: randFloat(-WORLD_RADIUS * 0.9, WORLD_RADIUS * 0.9),
    z: randFloat(-WORLD_RADIUS * 0.9, WORLD_RADIUS * 0.9),
    vx: randFloat(-0.02, 0.02),
    vz: randFloat(-0.02, 0.02),
    color: choose(HUMAN_COLORS)
  });
}

function mulberry32(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randFloat(min, max) {
  return min + rng() * (max - min);
}

function randInt(min, max) {
  return Math.floor(randFloat(min, max + 1));
}

function choose(list) {
  return list[Math.floor(rng() * list.length)];
}

function bgr(color) {
  const key = color.join(",");
  if (!colorCache.has(key)) {
    colorCache.set(key, `rgb(${color[2]}, ${color[1]}, ${color[0]})`);
  }
  return colorCache.get(key);
}

function bgrAlpha(color, alpha) {
  return `rgba(${color[2]}, ${color[1]}, ${color[0]}, ${alpha})`;
}

function rgb(r, g, b, alpha = 1) {
  return alpha === 1 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function selectedPart(category) {
  return TOOLBOX_PARTS[category][selectedParts[category]];
}

function cycleSelectedPart(category, step = 1) {
  if (category !== "Chassis" && selectedPart("Chassis") === "None") {
    return;
  }
  const parts = TOOLBOX_PARTS[category];
  const currentIndex = selectedParts[category];
  selectedParts[category] = (currentIndex + step + parts.length) % parts.length;
  if (category === "Chassis" && selectedPart("Chassis") === "None") {
    for (const key of TOOLBOX_CATEGORIES) {
      if (key !== "Chassis") {
        selectedParts[key] = 0;
      }
    }
  }
}

function applyManualPreset() {
  if (manualPresetApplied) {
    return;
  }
  manualPresetApplied = true;

  const allDisabled = TOOLBOX_CATEGORIES.every((category) => {
    const value = selectedPart(category);
    return value === "None" || value === "Off";
  });

  if (!allDisabled) {
    return;
  }

  selectedParts["Chassis"] = 1;
  selectedParts["Wheels (WASD)"] = 1;
  selectedParts["Lidar"] = 1;
  selectedParts["Camera (View)"] = 1;
  selectedParts["Arm (SPACE)"] = 2;
}

function setControlMode(mode, title, detail) {
  controlMode = mode;
  modeBannerTitle = title;
  modeBannerDetail = detail;
  if (mode === "manual") {
    applyManualPreset();
  }
}

function setFont(context, size, weight = 500) {
  context.font = `${weight} ${size}px "Segoe UI", Arial, sans-serif`;
}

function fillText(context, text, x, y, size, color, align = "left", weight = 500) {
  context.save();
  setFont(context, size, weight);
  context.fillStyle = color;
  context.textAlign = align;
  context.textBaseline = "alphabetic";
  context.fillText(text, x, y);
  context.restore();
}

function measureTextWidth(context, text, size, weight = 500) {
  context.save();
  setFont(context, size, weight);
  const width = context.measureText(text).width;
  context.restore();
  return width;
}

function roundedRectPath(context, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + r, y);
  context.lineTo(x + width - r, y);
  context.quadraticCurveTo(x + width, y, x + width, y + r);
  context.lineTo(x + width, y + height - r);
  context.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  context.lineTo(x + r, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - r);
  context.lineTo(x, y + r);
  context.quadraticCurveTo(x, y, x + r, y);
  context.closePath();
}

function fillRoundedRect(context, x, y, width, height, radius, fillStyle) {
  context.save();
  roundedRectPath(context, x, y, width, height, radius);
  context.fillStyle = fillStyle;
  context.fill();
  context.restore();
}

function strokeRoundedRect(context, x, y, width, height, radius, strokeStyle, lineWidth = 1) {
  context.save();
  roundedRectPath(context, x, y, width, height, radius);
  context.strokeStyle = strokeStyle;
  context.lineWidth = lineWidth;
  context.stroke();
  context.restore();
}

function drawTriangle(context, x, y, size, fillStyle, strokeStyle = rgb(255, 255, 255), lineWidth = 1) {
  context.save();
  context.beginPath();
  context.moveTo(x, y - size);
  context.lineTo(x - size, y + size);
  context.lineTo(x + size, y + size);
  context.closePath();
  context.fillStyle = fillStyle;
  context.fill();
  context.strokeStyle = strokeStyle;
  context.lineWidth = lineWidth;
  context.stroke();
  context.restore();
}

function drawObjectShape(context, object, x, y, size, overrideFill = null) {
  const fillStyle = overrideFill ?? bgr(object.color);
  if (object.shape === "circle") {
    context.save();
    context.beginPath();
    context.arc(x, y, size, 0, Math.PI * 2);
    context.fillStyle = fillStyle;
    context.fill();
    context.strokeStyle = rgb(255, 255, 255);
    context.lineWidth = 1;
    context.stroke();
    context.restore();
    return;
  }
  if (object.shape === "square") {
    context.save();
    context.fillStyle = fillStyle;
    context.fillRect(x - size, y - size, size * 2, size * 2);
    context.strokeStyle = rgb(255, 255, 255);
    context.lineWidth = 1;
    context.strokeRect(x - size, y - size, size * 2, size * 2);
    context.restore();
    return;
  }
  drawTriangle(context, x, y, size, fillStyle);
}

function fingersUp(landmarks) {
  const tips = [8, 12, 16, 20];
  const pips = [6, 10, 14, 18];
  return tips.map((tip, index) => landmarks[tip].y < landmarks[pips[index]].y);
}

function thumbUp(landmarks, handedness = "Right") {
  return handedness === "Right" ? landmarks[4].x < landmarks[3].x : landmarks[4].x > landmarks[3].x;
}

function classifyGesture(landmarks, handedness = "Right") {
  const [index, middle, ring, pinky] = fingersUp(landmarks);
  const thumb = thumbUp(landmarks, handedness);
  const upCount = [index, middle, ring, pinky].filter(Boolean).length;
  if (upCount === 0) {
    return "LAND";
  }
  if (upCount === 4 && thumb) {
    return "HOVER";
  }
  if (upCount === 4 && !thumb) {
    return "MOVE_LEFT";
  }
  if (upCount === 1 && index) {
    return "MOVE_FORWARD";
  }
  if (upCount === 2 && index && middle) {
    return "MOVE_BACKWARD";
  }
  if (upCount === 3 && index && middle && ring) {
    return "MOVE_RIGHT";
  }
  return "NONE";
}

function updateStableGesture(newGesture) {
  gestureHistory.push(newGesture);
  if (gestureHistory.length > GESTURE_STABLE_FRAMES) {
    gestureHistory.shift();
  }
  if (gestureHistory.length === GESTURE_STABLE_FRAMES && new Set(gestureHistory).size === 1) {
    stableGesture = gestureHistory[0];
  }
}

function updateStableActionGesture(newGesture) {
  actionGestureHistory.push(newGesture);
  if (actionGestureHistory.length > GESTURE_STABLE_FRAMES) {
    actionGestureHistory.shift();
  }
  if (actionGestureHistory.length === GESTURE_STABLE_FRAMES && new Set(actionGestureHistory).size === 1) {
    stableActionGesture = actionGestureHistory[0];
  }
}

function updateRobot() {
  if (robotFrozen) {
    robotState = "FROZEN";
    return;
  }

  const wheels = selectedPart("Wheels (WASD)");
  if (wheels === "None") {
    robotState = "IDLE";
    return;
  }

  if (stableGesture === "LAND") {
    const distToCenter = Math.sqrt(robotX * robotX + robotZ * robotZ);
    if (distToCenter < 0.3) {
      robotX = 0.0;
      robotZ = 0.0;
      robotState = "IDLE";
      return;
    }

    targetAngle = (Math.atan2(-robotX, -robotZ) * 180 / Math.PI + 360) % 360;
    let diff = (targetAngle - robotAngle + 180) % 360 - 180;
    if (Math.abs(diff) <= TURN_SPEED) {
      robotAngle = targetAngle;
    } else {
      robotAngle += diff > 0 ? TURN_SPEED : -TURN_SPEED;
    }
    robotAngle = (robotAngle + 360) % 360;

    diff = (targetAngle - robotAngle + 180) % 360 - 180;
    if (Math.abs(diff) < 30) {
      robotState = "WALKING";
      robotX += (-robotX / distToCenter) * ROBOT_SPEED;
      robotZ += (-robotZ / distToCenter) * ROBOT_SPEED;
    } else {
      robotState = "TURNING";
    }
  } else {
    let moving = false;
    if (stableGesture === "HOVER") {
      robotState = "STANDING";
    } else {
      if (stableGesture === "MOVE_FORWARD") {
        targetAngle = 180;
        moving = true;
      } else if (stableGesture === "MOVE_BACKWARD") {
        targetAngle = 0;
        moving = true;
      } else if (stableGesture === "MOVE_LEFT") {
        targetAngle = 270;
        moving = true;
      } else if (stableGesture === "MOVE_RIGHT") {
        targetAngle = 90;
        moving = true;
      }

      let diff = (targetAngle - robotAngle + 180) % 360 - 180;
      if (Math.abs(diff) <= TURN_SPEED) {
        robotAngle = targetAngle;
      } else {
        robotAngle += diff > 0 ? TURN_SPEED : -TURN_SPEED;
      }
      robotAngle = (robotAngle + 360) % 360;
      diff = (targetAngle - robotAngle + 180) % 360 - 180;

      if (moving && Math.abs(diff) < 25) {
        robotState = "WALKING";
        if (stableGesture === "MOVE_FORWARD") {
          robotZ -= ROBOT_SPEED;
        } else if (stableGesture === "MOVE_BACKWARD") {
          robotZ += ROBOT_SPEED;
        } else if (stableGesture === "MOVE_LEFT") {
          robotX -= ROBOT_SPEED;
        } else if (stableGesture === "MOVE_RIGHT") {
          robotX += ROBOT_SPEED;
        }
      } else if (moving) {
        robotState = "TURNING";
      } else {
        robotState = "STANDING";
      }
    }
  }

  const radius = Math.sqrt(robotX * robotX + robotZ * robotZ);
  if (radius > WORLD_RADIUS) {
    const scale = WORLD_RADIUS / radius;
    robotX *= scale;
    robotZ *= scale;
  }
}

function tryPickup() {
  if (heldObject !== null) {
    return;
  }
  if (selectedPart("Arm (SPACE)") !== "Extended") {
    return;
  }
  let bestDist = PICKUP_RANGE;
  let bestIndex = null;
  for (let i = 0; i < staticObjects.length; i += 1) {
    const object = staticObjects[i];
    const dx = object.x - robotX;
    const dz = object.z - robotZ;
    const dist = Math.hypot(dx, dz);
    if (dist < bestDist) {
      bestDist = dist;
      bestIndex = i;
    }
  }
  if (bestIndex !== null) {
    heldObject = staticObjects[bestIndex];
    heldObjectIndex = bestIndex;
  }
}

function tryDrop() {
  if (heldObject === null) {
    return;
  }
  heldObject.x = robotX;
  heldObject.z = robotZ;
  heldObject = null;
  heldObjectIndex = null;
}

function worldToScreen(wx, wz, centerX, horizonY, groundY, spanX) {
  const sx = centerX + (wx / WORLD_RADIUS) * spanX;
  const zNorm = (wz + WORLD_RADIUS) / (2 * WORLD_RADIUS);
  const sy = horizonY + zNorm * (groundY - horizonY);
  const scale = 0.3 + 0.7 * zNorm;
  return { x: sx, y: sy, scale };
}

function updateWanderingHumans() {
  for (const human of wanderingHumans) {
    human.x += human.vx;
    human.z += human.vz;
    if (Math.abs(human.x) > WORLD_RADIUS * 0.7) {
      human.vx *= -1;
      human.x = clamp(human.x, -WORLD_RADIUS * 0.7, WORLD_RADIUS * 0.7);
    }
    if (Math.abs(human.z) > WORLD_RADIUS * 0.7) {
      human.vz *= -1;
      human.z = clamp(human.z, -WORLD_RADIUS * 0.7, WORLD_RADIUS * 0.7);
    }
    if (rng() < 0.005) {
      human.vx = randFloat(-0.02, 0.02);
      human.vz = randFloat(-0.02, 0.02);
    }
  }
}

function drawStickFigure(context, x, y, scale, color) {
  const stroke = Array.isArray(color) ? bgr(color) : color;
  const s = Math.max(0.4, scale);
  const headRadius = Math.round(4 * s);
  const bodyLength = Math.round(14 * s);
  const legLength = Math.round(10 * s);
  const armLength = Math.round(8 * s);
  const headY = y - bodyLength - headRadius;

  context.save();
  context.strokeStyle = stroke;
  context.fillStyle = stroke;
  context.lineWidth = Math.max(1, Math.round(2 * s));
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();
  context.arc(x, headY, headRadius, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = rgb(255, 255, 255);
  context.lineWidth = 1;
  context.stroke();
  context.strokeStyle = stroke;
  context.lineWidth = Math.max(1, Math.round(2 * s));
  context.beginPath();
  context.moveTo(x, headY + headRadius);
  context.lineTo(x, y);
  context.moveTo(x, headY + headRadius + Math.round(4 * s));
  context.lineTo(x - armLength, headY + headRadius + Math.round(8 * s));
  context.moveTo(x, headY + headRadius + Math.round(4 * s));
  context.lineTo(x + armLength, headY + headRadius + Math.round(8 * s));
  context.moveTo(x, y);
  context.lineTo(x - Math.round(5 * s), y + legLength);
  context.moveTo(x, y);
  context.lineTo(x + Math.round(5 * s), y + legLength);
  context.stroke();
  context.restore();
}

function getLidarDetections(maxRange = 4.0) {
  const detections = [];
  for (let i = 0; i < staticObjects.length; i += 1) {
    if (i === heldObjectIndex) {
      continue;
    }
    const object = staticObjects[i];
    const dx = object.x - robotX;
    const dz = object.z - robotZ;
    const dist = Math.hypot(dx, dz);
    if (dist <= maxRange) {
      detections.push({ type: object.shape[0].toUpperCase() + object.shape.slice(1), dist });
    }
  }
  for (const human of wanderingHumans) {
    const dx = human.x - robotX;
    const dz = human.z - robotZ;
    const dist = Math.hypot(dx, dz);
    if (dist <= maxRange) {
      detections.push({ type: "Human", dist });
    }
  }
  detections.sort((a, b) => a.dist - b.dist);
  return detections;
}

function drawRobotModel(context, centerX, centerY, previewScale = 1) {
  const chassis = selectedPart("Chassis");
  const wheels = selectedPart("Wheels (WASD)");
  const lidar = selectedPart("Lidar");
  const camera = selectedPart("Camera (View)");
  const arm = selectedPart("Arm (SPACE)");

  if (chassis === "None" && wheels === "None" && lidar === "Off" && camera === "None" && arm === "None") {
    return;
  }

  const tempSize = 250;
  const tc = tempSize / 2;
  const s = previewScale;
  const t = frameSeconds;
  let bodyWidth = 0;
  let bodyHeight = 0;

  tempRobotCtx.clearRect(0, 0, tempSize, tempSize);
  tempRobotCtx.save();
  tempRobotCtx.lineCap = "round";
  tempRobotCtx.lineJoin = "round";

  const greenBody = [80, 180, 80];
  const greenBorder = [60, 220, 60];
  const blackWheel = [30, 30, 30];
  const wheelBorder = [80, 80, 80];
  const redLidar = [60, 60, 240];
  const blueCam = [240, 160, 40];
  const purpleArm = [200, 60, 200];
  const purpleDark = [150, 40, 150];

  if (chassis !== "None") {
    if (chassis === "Standard") {
      bodyWidth = Math.round(60 * s);
      bodyHeight = Math.round(45 * s);
    } else if (chassis === "Tank") {
      bodyWidth = Math.round(70 * s);
      bodyHeight = Math.round(50 * s);
    } else if (chassis === "Humanoid") {
      bodyWidth = Math.round(50 * s);
      bodyHeight = Math.round(55 * s);
    } else if (chassis === "Spider") {
      bodyWidth = Math.round(55 * s);
      bodyHeight = Math.round(55 * s);
    } else {
      bodyWidth = Math.round(60 * s);
      bodyHeight = Math.round(45 * s);
    }

    tempRobotCtx.fillStyle = bgr(greenBody);
    tempRobotCtx.fillRect(tc - bodyWidth / 2, tc - bodyHeight / 2, bodyWidth, bodyHeight);
    tempRobotCtx.strokeStyle = bgr(greenBorder);
    tempRobotCtx.lineWidth = 2;
    tempRobotCtx.strokeRect(tc - bodyWidth / 2, tc - bodyHeight / 2, bodyWidth, bodyHeight);
    tempRobotCtx.strokeStyle = bgr([70, 150, 70]);
    tempRobotCtx.lineWidth = 1;
    tempRobotCtx.beginPath();
    tempRobotCtx.moveTo(tc - bodyWidth / 2 + 6, tc);
    tempRobotCtx.lineTo(tc + bodyWidth / 2 - 6, tc);
    tempRobotCtx.stroke();
    if (chassis === "Tank") {
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc, tc - bodyHeight / 2 + 4);
      tempRobotCtx.lineTo(tc, tc + bodyHeight / 2 - 4);
      tempRobotCtx.stroke();
    } else if (chassis === "Spider") {
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc - bodyWidth / 3, tc - bodyHeight / 3);
      tempRobotCtx.lineTo(tc + bodyWidth / 3, tc + bodyHeight / 3);
      tempRobotCtx.moveTo(tc + bodyWidth / 3, tc - bodyHeight / 3);
      tempRobotCtx.lineTo(tc - bodyWidth / 3, tc + bodyHeight / 3);
      tempRobotCtx.stroke();
    }
  }

  const isMoving = robotState === "WALKING" || robotState === "TURNING";
  if (wheels !== "None" && chassis !== "None") {
    const wheelRadius = Math.round(14 * s);
    if (wheels === "Treads") {
      const treadWidth = Math.round(14 * s);
      const treadHeight = Math.round(bodyHeight * 0.95);
      for (const side of [-1, 1]) {
        const trackX = tc + side * (bodyWidth / 2 + treadWidth / 2 + Math.round(2 * s));
        tempRobotCtx.fillStyle = bgr(blackWheel);
        tempRobotCtx.fillRect(trackX - treadWidth / 2, tc - treadHeight / 2, treadWidth, treadHeight);
        tempRobotCtx.strokeStyle = bgr(wheelBorder);
        tempRobotCtx.lineWidth = 2;
        tempRobotCtx.strokeRect(trackX - treadWidth / 2, tc - treadHeight / 2, treadWidth, treadHeight);
        const spacing = Math.max(1, Math.floor(treadHeight / 6));
        const treadOffset = isMoving ? Math.floor((t * 80) % spacing) : 0;
        for (let j = 0; j < 8; j += 1) {
          const lineY = Math.floor(tc - treadHeight / 2 + j * spacing + treadOffset);
          if (lineY >= tc - treadHeight / 2 && lineY <= tc + treadHeight / 2) {
            tempRobotCtx.beginPath();
            tempRobotCtx.moveTo(trackX - treadWidth / 2 + 2, lineY);
            tempRobotCtx.lineTo(trackX + treadWidth / 2 - 2, lineY);
            tempRobotCtx.strokeStyle = bgr(wheelBorder);
            tempRobotCtx.lineWidth = 1;
            tempRobotCtx.stroke();
          }
        }
      }
    } else if (wheels === "Legs") {
      const corners = [[-1, -1], [1, -1], [-1, 1], [1, 1]];
      corners.forEach(([sx, sy], index) => {
        const phase = isMoving ? Math.sin(t * 8 + index * Math.PI / 2) : 0;
        const legExtend = Math.round(6 * s + phase * 4 * s);
        const legX = tc + sx * (bodyWidth / 2 + legExtend);
        const legY = tc + sy * (bodyHeight / 2 - Math.round(4 * s));
        tempRobotCtx.beginPath();
        tempRobotCtx.fillStyle = bgr(blackWheel);
        tempRobotCtx.arc(legX, legY, Math.round(7 * s), 0, Math.PI * 2);
        tempRobotCtx.fill();
        tempRobotCtx.strokeStyle = bgr(wheelBorder);
        tempRobotCtx.lineWidth = 2;
        tempRobotCtx.stroke();
        tempRobotCtx.beginPath();
        tempRobotCtx.moveTo(tc + sx * (bodyWidth / 2), legY);
        tempRobotCtx.lineTo(legX, legY);
        tempRobotCtx.strokeStyle = bgr([100, 100, 100]);
        tempRobotCtx.lineWidth = Math.max(1, Math.round(2 * s));
        tempRobotCtx.stroke();
      });
    } else {
      const corners = [[-1, -1], [1, -1], [-1, 1], [1, 1]];
      corners.forEach(([sx, sy], index) => {
        const wheelX = tc + sx * (bodyWidth / 2 + Math.round(4 * s));
        const wheelY = tc + sy * (bodyHeight / 2 - Math.round(2 * s));
        tempRobotCtx.beginPath();
        tempRobotCtx.fillStyle = bgr(blackWheel);
        tempRobotCtx.arc(wheelX, wheelY, wheelRadius, 0, Math.PI * 2);
        tempRobotCtx.fill();
        tempRobotCtx.strokeStyle = bgr(wheelBorder);
        tempRobotCtx.lineWidth = 2;
        tempRobotCtx.stroke();
        tempRobotCtx.beginPath();
        tempRobotCtx.fillStyle = bgr([60, 60, 60]);
        tempRobotCtx.arc(wheelX, wheelY, Math.round(5 * s), 0, Math.PI * 2);
        tempRobotCtx.fill();
        tempRobotCtx.strokeStyle = bgr(wheelBorder);
        tempRobotCtx.lineWidth = 1;
        tempRobotCtx.stroke();
        const spokeRadius = wheelRadius - 2;
        for (let spoke = 0; spoke < 3; spoke += 1) {
          const angle = (isMoving ? t * 10 : 0) + spoke * Math.PI * 2 / 3 + (isMoving ? index * 0.3 : 0);
          const dx = spokeRadius * Math.cos(angle);
          const dy = spokeRadius * Math.sin(angle);
          tempRobotCtx.beginPath();
          tempRobotCtx.moveTo(wheelX, wheelY);
          tempRobotCtx.lineTo(wheelX + dx, wheelY + dy);
          tempRobotCtx.strokeStyle = bgr(wheelBorder);
          tempRobotCtx.lineWidth = isMoving ? 2 : 1;
          tempRobotCtx.stroke();
        }
      });
    }
  }

  if (lidar === "On" && chassis !== "None") {
    const lidarX = tc;
    const lidarY = tc - Math.round(8 * s);
    const scanRadius = Math.round(12 * s + Math.abs(Math.sin(t * 8)) * 6);
    tempRobotCtx.save();
    tempRobotCtx.shadowBlur = Math.round(18 * s);
    tempRobotCtx.shadowColor = bgr(redLidar);
    tempRobotCtx.beginPath();
    tempRobotCtx.fillStyle = bgr(redLidar);
    tempRobotCtx.arc(lidarX, lidarY, Math.round(8 * s), 0, Math.PI * 2);
    tempRobotCtx.fill();
    tempRobotCtx.restore();
    tempRobotCtx.beginPath();
    tempRobotCtx.arc(lidarX, lidarY, Math.round(8 * s), 0, Math.PI * 2);
    tempRobotCtx.strokeStyle = bgr([80, 80, 255]);
    tempRobotCtx.lineWidth = 2;
    tempRobotCtx.stroke();
    tempRobotCtx.beginPath();
    tempRobotCtx.arc(lidarX, lidarY, scanRadius, 0, Math.PI * 2);
    tempRobotCtx.strokeStyle = bgr([80, 80, 255]);
    tempRobotCtx.lineWidth = 1;
    tempRobotCtx.stroke();
  }

  if (camera !== "None" && chassis !== "None") {
    const camX = tc;
    const camY = tc + Math.round(10 * s);
    const camRadius = camera === "Standard" ? Math.round(5 * s) : camera === "Wide-Angle" ? Math.round(7 * s) : Math.round(6 * s);
    tempRobotCtx.beginPath();
    tempRobotCtx.arc(camX, camY, camRadius, 0, Math.PI * 2);
    if (camera === "Thermal") {
      tempRobotCtx.fillStyle = bgr([0, 100, 255]);
      tempRobotCtx.fill();
      tempRobotCtx.strokeStyle = bgr([0, 140, 255]);
    } else {
      tempRobotCtx.fillStyle = bgr(blueCam);
      tempRobotCtx.fill();
      tempRobotCtx.strokeStyle = bgr([255, 200, 80]);
    }
    tempRobotCtx.lineWidth = 2;
    tempRobotCtx.stroke();
    tempRobotCtx.beginPath();
    tempRobotCtx.arc(camX - Math.round(1 * s), camY - Math.round(1 * s), Math.max(1, Math.round(1 * s)), 0, Math.PI * 2);
    tempRobotCtx.fillStyle = rgb(255, 255, 255);
    tempRobotCtx.fill();
  }

  if (arm !== "None" && chassis !== "None") {
    const armBaseY = tc - bodyHeight / 2;
    tempRobotCtx.strokeStyle = bgr(purpleArm);
    tempRobotCtx.lineCap = "round";
    tempRobotCtx.lineJoin = "round";
    if (arm === "Extended") {
      const armTopY = armBaseY - Math.round(30 * s);
      const forearmTopY = armTopY - Math.round(20 * s);
      const gripLength = Math.round(12 * s);
      const gripSpread = heldObject !== null ? Math.round(4 * s) : gripLength;
      tempRobotCtx.lineWidth = Math.max(2, Math.round(5 * s));
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc, armBaseY);
      tempRobotCtx.lineTo(tc, armTopY);
      tempRobotCtx.stroke();
      tempRobotCtx.beginPath();
      tempRobotCtx.fillStyle = bgr(purpleDark);
      tempRobotCtx.arc(tc, armTopY, Math.round(4 * s), 0, Math.PI * 2);
      tempRobotCtx.fill();
      tempRobotCtx.strokeStyle = bgr(purpleArm);
      tempRobotCtx.lineWidth = 2;
      tempRobotCtx.stroke();
      tempRobotCtx.lineWidth = Math.max(2, Math.round(4 * s));
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc, armTopY);
      tempRobotCtx.lineTo(tc, forearmTopY);
      tempRobotCtx.stroke();
      tempRobotCtx.save();
      tempRobotCtx.shadowBlur = 10;
      tempRobotCtx.shadowColor = bgr(purpleArm);
      tempRobotCtx.beginPath();
      tempRobotCtx.arc(tc, forearmTopY, Math.round(3 * s), 0, Math.PI * 2);
      tempRobotCtx.fillStyle = bgr(purpleArm);
      tempRobotCtx.fill();
      tempRobotCtx.restore();
      tempRobotCtx.lineWidth = Math.max(2, Math.round(3 * s));
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc, forearmTopY);
      tempRobotCtx.lineTo(tc - gripSpread, forearmTopY - gripLength);
      tempRobotCtx.moveTo(tc, forearmTopY);
      tempRobotCtx.lineTo(tc + gripSpread, forearmTopY - gripLength);
      tempRobotCtx.stroke();
      tempRobotCtx.beginPath();
      tempRobotCtx.fillStyle = bgr(purpleDark);
      tempRobotCtx.arc(tc - gripSpread, forearmTopY - gripLength, Math.round(3 * s), 0, Math.PI * 2);
      tempRobotCtx.arc(tc + gripSpread, forearmTopY - gripLength, Math.round(3 * s), 0, Math.PI * 2);
      tempRobotCtx.fill();
      if (heldObject !== null) {
        const gripTipY = forearmTopY - Math.round(gripLength * 0.7);
        const objectSize = Math.round(heldObject.size * s * 0.8);
        drawObjectShape(tempRobotCtx, heldObject, tc, gripTipY, objectSize, bgr(heldObject.color));
      }
    } else {
      const armTopY = armBaseY - Math.round(15 * s);
      tempRobotCtx.lineWidth = Math.max(2, Math.round(5 * s));
      tempRobotCtx.beginPath();
      tempRobotCtx.moveTo(tc, armBaseY);
      tempRobotCtx.lineTo(tc, armTopY);
      tempRobotCtx.stroke();
      tempRobotCtx.beginPath();
      tempRobotCtx.fillStyle = bgr(purpleDark);
      tempRobotCtx.arc(tc, armTopY, Math.round(4 * s), 0, Math.PI * 2);
      tempRobotCtx.fill();
      tempRobotCtx.strokeStyle = bgr(purpleArm);
      tempRobotCtx.lineWidth = 2;
      tempRobotCtx.stroke();
    }
  }

  tempRobotCtx.restore();

  context.save();
  context.translate(centerX, centerY);
  context.rotate((robotAngle + 180) * Math.PI / 180);
  context.drawImage(tempRobotCanvas, -tempSize / 2, -tempSize / 2);
  context.restore();
}

function updateToolboxLogic(x, y, isPinching, nowSeconds) {
  const boxSize = 100;
  const padding = 15;
  const totalWidth = TOOLBOX_CATEGORIES.length * boxSize + (TOOLBOX_CATEGORIES.length - 1) * padding;
  const startX = (SIM_W - totalWidth) / 2;
  const startY = 65;

  let cursorInUi = false;
  if (x >= startX && x <= startX + totalWidth && y >= startY && y <= startY + boxSize) {
    cursorInUi = true;
  }

  const chassisEquipped = selectedPart("Chassis") !== "None";
  if (!chassisEquipped) {
    for (const category of TOOLBOX_CATEGORIES) {
      if (category !== "Chassis") {
        selectedParts[category] = 0;
      }
    }
  }

  let currentHover = null;
  TOOLBOX_CATEGORIES.forEach((category, index) => {
    const boxX = startX + index * (boxSize + padding);
    const boxY = startY;
    const isHover = x >= boxX && x <= boxX + boxSize && y >= boxY && y <= boxY + boxSize;
    if (!isHover) {
      return;
    }
    currentHover = category;
    if (category !== "Chassis" && !chassisEquipped) {
      return;
    }
    if (lastHoveredCat !== category) {
      if (selectedParts[category] === 0 && TOOLBOX_PARTS[category].length > 1) {
        selectedParts[category] = 1;
      } else {
        selectedParts[category] = 0;
      }
    }
    if (isPinching && nowSeconds - lastClickTime > CLICK_COOLDOWN) {
      selectedParts[category] = (selectedParts[category] + 1) % TOOLBOX_PARTS[category].length;
      lastClickTime = nowSeconds;
    }
  });

  lastHoveredCat = currentHover;
  return cursorInUi;
}

function drawToolbox(context, x, y) {
  const boxSize = 100;
  const padding = 15;
  const totalWidth = TOOLBOX_CATEGORIES.length * boxSize + (TOOLBOX_CATEGORIES.length - 1) * padding;
  const startX = (SIM_W - totalWidth) / 2;
  const startY = 65;
  const cornerRadius = 12;
  const chassisEquipped = selectedPart("Chassis") !== "None";

  fillText(context, "Toolbox", SIM_W / 2, 50, 30, rgb(255, 255, 255), "center", 700);

  TOOLBOX_CATEGORIES.forEach((category, index) => {
    const boxX = startX + index * (boxSize + padding);
    const boxY = startY;
    const isHover = x >= boxX && x <= boxX + boxSize && y >= boxY && y <= boxY + boxSize;
    const locked = category !== "Chassis" && !chassisEquipped;
    const color = locked ? rgb(40, 40, 40) : bgr(TOOLBOX_COLORS[index]);
    const activePart = selectedPart(category);
    const shortName = category.split(" (")[0];
    const isOn = activePart !== "None" && activePart !== "Off";
    const label = locked ? "--" : isOn ? "On" : "Off";
    const textColor = locked ? rgb(80, 80, 80) : rgb(255, 255, 255);

    fillRoundedRect(context, boxX, boxY, boxSize, boxSize, cornerRadius, color);
    if (isHover && !locked) {
      strokeRoundedRect(context, boxX - 2, boxY - 2, boxSize + 4, boxSize + 4, cornerRadius, rgb(255, 255, 255), 2);
    }

    fillText(context, shortName, boxX + boxSize / 2, boxY + 45, 18, textColor, "center", 500);
    fillText(context, label, boxX + boxSize / 2, boxY + 70, 20, textColor, "center", 700);
  });
}

function renderRobotCameraView() {
  const viewWidth = robotViewCanvas.width;
  const viewHeight = robotViewCanvas.height;
  const camType = selectedPart("Camera (View)");

  robotViewCtx.clearRect(0, 0, viewWidth, viewHeight);

  if (camType === "None") {
    robotViewCtx.fillStyle = rgb(0, 0, 0);
    robotViewCtx.fillRect(0, 0, viewWidth, viewHeight);
    fillText(robotViewCtx, "NO CAMERA", viewWidth / 2, viewHeight / 2, 18, rgb(60, 60, 60), "center", 600);
    return;
  }

  const fovMap = { "Standard": 60, "Wide-Angle": 100, "Thermal": 60 };
  const rangeMap = { "Standard": 5.0, "Wide-Angle": 5.0, "Thermal": 7.0 };
  const fovDeg = fovMap[camType] ?? 60;
  const maxRange = rangeMap[camType] ?? 5.0;
  const halfFov = (fovDeg * Math.PI / 180) / 2;
  const isThermal = camType === "Thermal";
  const horizon = Math.floor(viewHeight / 3);

  robotViewCtx.fillStyle = isThermal ? bgr([40, 20, 10]) : bgr([50, 40, 20]);
  robotViewCtx.fillRect(0, 0, viewWidth, horizon);
  robotViewCtx.fillStyle = isThermal ? bgr([50, 35, 15]) : bgr([40, 55, 40]);
  robotViewCtx.fillRect(0, horizon, viewWidth, viewHeight - horizon);

  for (let i = 1; i < 8; i += 1) {
    const gridY = horizon + Math.floor((viewHeight - horizon) * i / 8);
    robotViewCtx.beginPath();
    robotViewCtx.moveTo(0, gridY);
    robotViewCtx.lineTo(viewWidth, gridY);
    robotViewCtx.strokeStyle = isThermal ? bgr([60, 40, 20]) : bgr([60, 70, 50]);
    robotViewCtx.lineWidth = 1;
    robotViewCtx.stroke();
  }

  const robotRad = robotAngle * Math.PI / 180;
  const visible = [];

  for (let i = 0; i < staticObjects.length; i += 1) {
    if (i === heldObjectIndex) {
      continue;
    }
    const object = staticObjects[i];
    const dx = object.x - robotX;
    const dz = object.z - robotZ;
    const dist = Math.hypot(dx, dz);
    if (dist > maxRange || dist < 0.3) {
      continue;
    }
    let relAngle = Math.atan2(dx, dz) - robotRad;
    relAngle = ((relAngle + Math.PI) % (Math.PI * 2)) - Math.PI;
    if (Math.abs(relAngle) < halfFov) {
      visible.push({ type: "obj", data: object, dist, angle: relAngle });
    }
  }

  for (const human of wanderingHumans) {
    const dx = human.x - robotX;
    const dz = human.z - robotZ;
    const dist = Math.hypot(dx, dz);
    if (dist > maxRange || dist < 0.3) {
      continue;
    }
    let relAngle = Math.atan2(dx, dz) - robotRad;
    relAngle = ((relAngle + Math.PI) % (Math.PI * 2)) - Math.PI;
    if (Math.abs(relAngle) < halfFov) {
      visible.push({ type: "human", data: human, dist, angle: relAngle });
    }
  }

  visible.sort((a, b) => b.dist - a.dist);

  for (const item of visible) {
    const screenX = viewWidth / 2 - (item.angle / halfFov) * (viewWidth / 2);
    const depthFrac = 1.0 - item.dist / maxRange;
    const screenY = horizon + (viewHeight - horizon) * (0.2 + 0.7 * depthFrac);
    const scale = 0.3 + 0.7 * depthFrac;

    if (item.type === "obj") {
      const object = item.data;
      const size = Math.round(object.size * scale * 1.5);
      const fillStyle = isThermal
        ? bgr([0, Math.round(80 + 100 * depthFrac), Math.round(150 + 100 * depthFrac)])
        : bgr(object.color);
      drawObjectShape(robotViewCtx, object, screenX, screenY, size, fillStyle);
    } else {
      const humanScale = scale * 0.8;
      const depthColor = isThermal
        ? [0, Math.round(100 + 155 * depthFrac), Math.round(200 + 55 * depthFrac)]
        : item.data.color;
      drawStickFigure(robotViewCtx, screenX, screenY, humanScale, depthColor);
    }
  }

  const crossX = viewWidth / 2;
  const crossY = viewHeight / 2;
  const crossColor = bgr([0, 200, 200]);
  robotViewCtx.save();
  robotViewCtx.strokeStyle = crossColor;
  robotViewCtx.lineWidth = 1;
  robotViewCtx.beginPath();
  robotViewCtx.moveTo(crossX - 8, crossY);
  robotViewCtx.lineTo(crossX - 3, crossY);
  robotViewCtx.moveTo(crossX + 3, crossY);
  robotViewCtx.lineTo(crossX + 8, crossY);
  robotViewCtx.moveTo(crossX, crossY - 8);
  robotViewCtx.lineTo(crossX, crossY - 3);
  robotViewCtx.moveTo(crossX, crossY + 3);
  robotViewCtx.lineTo(crossX, crossY + 8);
  robotViewCtx.stroke();
  robotViewCtx.restore();
}

function drawStatusPanel(context) {
  const panelWidth = 600;
  const panelHeight = 200;
  const panelX = 10;
  const panelY = SIM_H - panelHeight - 10;

  context.save();
  context.fillStyle = rgb(20, 20, 20, 0.7);
  context.fillRect(panelX, panelY, panelWidth, panelHeight);
  context.strokeStyle = rgb(100, 100, 100);
  context.lineWidth = 1;
  context.strokeRect(panelX, panelY, panelWidth, panelHeight);
  fillText(context, "EQUIPPED", panelX + 10, panelY + 24, 20, rgb(200, 200, 200), "left", 600);
  context.beginPath();
  context.moveTo(panelX + 10, panelY + 30);
  context.lineTo(panelX + 120, panelY + 30);
  context.strokeStyle = rgb(80, 80, 80);
  context.stroke();

  let row = 0;
  const partLabels = [
    ["Chassis", TOOLBOX_COLORS[0]],
    ["Wheels (WASD)", TOOLBOX_COLORS[1]],
    ["Lidar", TOOLBOX_COLORS[2]],
    ["Camera (View)", TOOLBOX_COLORS[3]],
    ["Arm (SPACE)", TOOLBOX_COLORS[4]]
  ];

  for (const [category, color] of partLabels) {
    const value = selectedPart(category);
    if (value === "None" || value === "Off") {
      continue;
    }
    const shortCategory = category.split(" (")[0];
    const text = `${shortCategory}: ${value}`;
    const textY = panelY + 50 + row * 22;
    context.beginPath();
    context.fillStyle = bgr(color);
    context.arc(panelX + 16, textY - 5, 5, 0, Math.PI * 2);
    context.fill();
    fillText(context, text, panelX + 28, textY, 18, rgb(220, 220, 220), "left", 500);
    row += 1;
  }

  if (row === 0) {
    fillText(context, "No parts equipped", panelX + 16, panelY + 55, 17, rgb(120, 120, 120), "left", 500);
  }

  if (heldObject !== null) {
    const textY = panelY + 50 + row * 22;
    context.beginPath();
    context.fillStyle = bgr(heldObject.color);
    context.arc(panelX + 16, textY - 5, 5, 0, Math.PI * 2);
    context.fill();
    fillText(context, `Holding: ${heldObject.shape[0].toUpperCase() + heldObject.shape.slice(1)}`, panelX + 28, textY, 18, bgr([0, 200, 255]), "left", 600);
  }

  const lidarX = panelX + 280;
  context.beginPath();
  context.moveTo(lidarX - 5, panelY + 8);
  context.lineTo(lidarX - 5, panelY + panelHeight - 8);
  context.strokeStyle = rgb(60, 60, 60);
  context.stroke();
  fillText(context, "LIDAR SCAN", lidarX + 6, panelY + 24, 20, bgr([100, 100, 240]), "left", 600);
  context.beginPath();
  context.moveTo(lidarX + 6, panelY + 30);
  context.lineTo(lidarX + 140, panelY + 30);
  context.strokeStyle = rgb(80, 80, 80);
  context.stroke();

  if (selectedPart("Lidar") !== "On") {
    fillText(context, "OFFLINE", lidarX + 16, panelY + 60, 18, rgb(80, 80, 80), "left", 500);
  } else {
    const detections = getLidarDetections();
    if (detections.length === 0) {
      fillText(context, "No contacts", lidarX + 16, panelY + 60, 17, bgr([80, 200, 80]), "left", 500);
    } else {
      detections.slice(0, 8).forEach((detection, index) => {
        const entryY = panelY + 50 + index * 20;
        const distText = `${detection.dist.toFixed(1)}m`;
        const label = `${detection.type} - ${distText}`;
        const color = detection.dist < 1.5
          ? [50, 50, 255]
          : detection.dist < 3.0
            ? [50, 200, 255]
            : [80, 200, 80];
        context.beginPath();
        context.fillStyle = bgr(color);
        context.arc(lidarX + 12, entryY - 4, 4, 0, Math.PI * 2);
        context.fill();
        fillText(context, label, lidarX + 24, entryY, 16, bgr(color), "left", 500);
      });
    }
  }

  context.restore();
}

function drawSim() {
  ctx.clearRect(0, 0, SIM_W, SIM_H);
  ctx.fillStyle = rgb(0, 0, 0);
  ctx.fillRect(0, 0, SIM_W, SIM_H);

  const centerX = SIM_W / 2;
  const groundY = SIM_H * 0.75;
  const horizonY = SIM_H * 0.25;
  const spanX = SIM_W * 0.4;
  const numLines = 60;

  ctx.save();
  ctx.strokeStyle = bgr([30, 50, 50]);
  ctx.lineWidth = 1;
  for (let i = -numLines; i <= numLines; i += 1) {
    const xBottom = centerX + i * 30;
    const xTop = centerX + i * 10;
    ctx.beginPath();
    ctx.moveTo(xBottom, groundY);
    ctx.lineTo(xTop, horizonY);
    ctx.stroke();
  }
  ctx.strokeStyle = bgr([25, 45, 45]);
  for (let j = 1; j < 10; j += 1) {
    const t = j / 10;
    const y = horizonY + t * (groundY - horizonY);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(SIM_W, y);
    ctx.stroke();
  }
  ctx.restore();

  for (let i = 0; i < staticObjects.length; i += 1) {
    if (i === heldObjectIndex) {
      continue;
    }
    const object = staticObjects[i];
    const screen = worldToScreen(object.x, object.z, centerX, horizonY, groundY, spanX);
    drawObjectShape(ctx, object, screen.x, screen.y, Math.round(object.size * screen.scale));
  }

  updateWanderingHumans();
  for (const human of wanderingHumans) {
    const screen = worldToScreen(human.x, human.z, centerX, horizonY, groundY, spanX);
    drawStickFigure(ctx, screen.x, screen.y, screen.scale, human.color);
  }

  const robotScreen = worldToScreen(robotX, robotZ, centerX, horizonY, groundY, spanX);
  drawRobotModel(ctx, robotScreen.x, robotScreen.y, 1);

  if (selectedPart("Arm (SPACE)") === "Extended" && heldObject === null) {
    for (const object of staticObjects) {
      const dx = object.x - robotX;
      const dz = object.z - robotZ;
      const dist = Math.hypot(dx, dz);
      if (dist < PICKUP_RANGE) {
        const screen = worldToScreen(object.x, object.z, centerX, horizonY, groundY, spanX);
        const radius = Math.round(object.size * screen.scale) + 6;
        const pulse = Math.abs(Math.sin(frameSeconds * 5)) * 0.5 + 0.5;
        ctx.save();
        ctx.beginPath();
        ctx.arc(screen.x, screen.y, radius, 0, Math.PI * 2);
        ctx.strokeStyle = bgr([0, Math.round(255 * pulse), Math.round(255 * pulse)]);
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();
        break;
      }
    }
  }

  for (let i = 0; i < 3; i += 1) {
    const lightX = robotScreen.x - 10 + i * 10;
    const lightPulse = Math.abs(Math.sin(frameSeconds * 3 + i * 0.5)) * 0.8 + 0.2;
    let lightColor = [0, 0, Math.round(255 * lightPulse)];
    if (robotState === "STANDING") {
      lightColor = [0, Math.round(255 * lightPulse), Math.round(255 * lightPulse)];
    } else if (robotState === "TURNING") {
      lightColor = [0, Math.round(200 * lightPulse), Math.round(255 * lightPulse)];
    } else if (robotState === "FROZEN") {
      lightColor = [Math.round(255 * lightPulse), 0, Math.round(128 * lightPulse)];
    } else if (robotState === "WALKING") {
      lightColor = [0, Math.round(255 * lightPulse), 0];
    }
    ctx.save();
    ctx.beginPath();
    ctx.arc(lightX, robotScreen.y - 14, 2, 0, Math.PI * 2);
    ctx.fillStyle = bgr(lightColor);
    ctx.fill();
    ctx.restore();
  }
}

function drawCursor() {
  const cursorColor = pinching ? bgr([0, 255, 0]) : bgr([0, 200, 255]);
  ctx.save();
  ctx.beginPath();
  ctx.arc(cursorX, cursorY, 10, 0, Math.PI * 2);
  ctx.fillStyle = cursorColor;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cursorX, cursorY, 14, 0, Math.PI * 2);
  ctx.strokeStyle = rgb(255, 255, 255);
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();
}

function drawPip() {
  const pipSize = 380;
  const pipX = SIM_W - pipSize - 20;
  const pipY = SIM_H - pipSize - 20;
  const hasCameraFeed = cameraAvailable && video.readyState >= 2;

  if (hasCameraFeed) {
    const cropSize = Math.min(CAM_W, CAM_H);
    const cropX = (CAM_W - cropSize) / 2;
    const cropY = (CAM_H - cropSize) / 2;
    ctx.drawImage(detectionCanvas, cropX, cropY, cropSize, cropSize, pipX, pipY, pipSize, pipSize);
  } else {
    ctx.save();
    ctx.fillStyle = rgb(6, 10, 14);
    ctx.fillRect(pipX, pipY, pipSize, pipSize);
    fillText(ctx, "ROBOTIC PANEL", pipX + pipSize / 2, pipY + 64, 28, bgr([255, 200, 0]), "center", 700);
    fillText(ctx, "Camera feed unavailable", pipX + pipSize / 2, pipY + 118, 18, rgb(200, 200, 200), "center", 500);
    fillText(ctx, "Manual control is active", pipX + pipSize / 2, pipY + 148, 18, rgb(170, 170, 170), "center", 500);
    fillText(ctx, "W / A / S / D", pipX + pipSize / 2, pipY + 216, 24, bgr([0, 170, 255]), "center", 700);
    fillText(ctx, "Move the robot", pipX + pipSize / 2, pipY + 246, 17, rgb(210, 210, 210), "center", 500);
    fillText(ctx, "1-5", pipX + pipSize / 2, pipY + 294, 24, bgr([0, 170, 255]), "center", 700);
    fillText(ctx, "Cycle chassis, wheels, lidar, camera, arm", pipX + pipSize / 2, pipY + 322, 16, rgb(210, 210, 210), "center", 500);
    fillText(ctx, "Space pick/drop", pipX + pipSize / 2, pipY + 350, 16, rgb(170, 170, 170), "center", 500);
    ctx.restore();
  }

  ctx.save();
  ctx.strokeStyle = bgr([255, 200, 0]);
  ctx.lineWidth = 2;
  ctx.strokeRect(pipX, pipY, pipSize, pipSize);
  ctx.restore();

  if (selectedPart("Camera (View)") !== "None") {
    renderRobotCameraView();
    const viewWidth = robotViewCanvas.width;
    const viewHeight = robotViewCanvas.height;
    const viewX = pipX - viewWidth - 6;
    const viewY = pipY + pipSize - viewHeight;
    ctx.drawImage(robotViewCanvas, viewX, viewY);
    ctx.save();
    ctx.strokeStyle = bgr([255, 200, 0]);
    ctx.lineWidth = 1;
    ctx.strokeRect(viewX, viewY, viewWidth, viewHeight);
    ctx.beginPath();
    ctx.fillStyle = bgr([0, 0, 220]);
    ctx.arc(viewX + 10, viewY + 12, 4, 0, Math.PI * 2);
    ctx.fill();
    fillText(ctx, "Live", viewX + 18, viewY + 16, 14, rgb(255, 255, 255), "left", 500);
    ctx.restore();
  }
}

function drawFrozenLabel() {
  fillText(ctx, "FROZEN", SIM_W / 2, 35, 36, bgr([0, 80, 255]), "center", 700);
}

function drawModeBanner(context) {
  const panelWidth = 640;
  const panelHeight = 72;
  const panelX = SIM_W - panelWidth - 24;
  const panelY = 24;
  const accent = controlMode === "manual" ? [0, 170, 255] : [0, 220, 180];
  const shortcutText = controlMode === "manual"
    ? "WASD move | 1-5 cycle parts | Space pick/drop | Q stop"
    : "Right hand aims and moves | Left hand freezes and picks";

  fillRoundedRect(context, panelX, panelY, panelWidth, panelHeight, 16, rgb(10, 16, 18, 0.86));
  strokeRoundedRect(context, panelX, panelY, panelWidth, panelHeight, 16, bgr(accent), 1);
  fillText(context, modeBannerTitle, panelX + 20, panelY + 28, 20, bgr(accent), "left", 700);
  fillText(context, modeBannerDetail, panelX + 20, panelY + 50, 15, rgb(220, 220, 220), "left", 500);
  fillText(context, shortcutText, panelX + panelWidth - 20, panelY + 50, 15, rgb(170, 170, 170), "right", 500);
}

function drawBootScreen() {
  ctx.clearRect(0, 0, SIM_W, SIM_H);
  ctx.fillStyle = rgb(0, 0, 0);
  ctx.fillRect(0, 0, SIM_W, SIM_H);
  ctx.save();
  ctx.strokeStyle = bgr([25, 45, 45]);
  ctx.lineWidth = 1;
  for (let i = 0; i < 18; i += 1) {
    const y = 140 + i * 42;
    ctx.beginPath();
    ctx.moveTo(260, y);
    ctx.lineTo(SIM_W - 260, y);
    ctx.stroke();
  }
  for (let i = 0; i < 22; i += 1) {
    const x = 240 + i * 66;
    ctx.beginPath();
    ctx.moveTo(x, 160);
    ctx.lineTo(x, SIM_H - 160);
    ctx.stroke();
  }
  ctx.restore();
  fillText(ctx, bootTitle, SIM_W / 2, SIM_H / 2 - 24, 42, bootError ? bgr([40, 80, 255]) : bgr([255, 200, 0]), "center", 700);
  fillText(ctx, bootDetail, SIM_W / 2, SIM_H / 2 + 24, 22, rgb(180, 180, 180), "center", 500);
}

function setBootScreen(title, detail, isError = false) {
  bootTitle = title;
  bootDetail = detail;
  bootError = isError;
  drawBootScreen();
}

function stopApp() {
  if (!running) {
    return;
  }
  running = false;
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
  setBootScreen("STOPPED", "Reload the page to start again");
}

async function loadVisionModule() {
  const errors = [];
  for (const source of MEDIAPIPE_SOURCES) {
    try {
      const loaded = await import(source.moduleUrl);
      if (!loaded?.FilesetResolver || !loaded?.HandLandmarker) {
        throw new Error("MediaPipe module loaded without required exports");
      }
      activeWasmRoot = source.wasmRoot;
      return loaded;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errors.push(`${source.moduleUrl} -> ${message}`);
    }
  }
  throw new Error(`Could not load MediaPipe Tasks Vision. ${errors[0] ?? "Unknown error"}`);
}

function processDetections(results, nowMs) {
  currentGesture = "NONE";
  actionGesture = "NONE";
  pinching = false;
  showCursor = false;
  cursorX = -100;
  cursorY = -100;

  const landmarksList = results?.landmarks ?? [];
  const handednessList = results?.handedness ?? results?.handednesses ?? [];

  if (landmarksList.length > 0) {
    let movementLm = null;
    let actionLm = null;
    let movementHandedness = "Right";

    for (let i = 0; i < landmarksList.length; i += 1) {
      const label = handednessList[i]?.[0]?.categoryName ?? "Right";
      if (label === "Right") {
        movementLm = landmarksList[i];
        movementHandedness = "Right";
      } else if (label === "Left") {
        actionLm = landmarksList[i];
      }
    }

    if (movementLm === null && actionLm !== null) {
      movementLm = actionLm;
      movementHandedness = "Left";
      actionLm = null;
    }

    if (movementLm !== null) {
      cursorX = movementLm[8].x * SIM_W;
      cursorY = movementLm[8].y * SIM_H;
      pinching = Math.hypot(movementLm[8].x - movementLm[4].x, movementLm[8].y - movementLm[4].y) < 0.05;
      currentGesture = classifyGesture(movementLm, movementHandedness);
      showCursor = true;
    }

    if (actionLm !== null) {
      actionGesture = classifyGesture(actionLm, "Left");
    }
  }

  updateStableGesture(currentGesture);
  updateStableActionGesture(actionGesture);

  robotFrozen = stableActionGesture === "HOVER";

  const currentActionFist = stableActionGesture === "LAND";
  if (currentActionFist && !prevActionFist) {
    if (heldObject === null) {
      tryPickup();
    } else {
      tryDrop();
    }
  }
  prevActionFist = currentActionFist;

  const cursorInUi = updateToolboxLogic(cursorX, cursorY, pinching, nowMs / 1000);
  if (!cursorInUi) {
    updateRobot();
  }

  if (heldObject !== null && selectedPart("Arm (SPACE)") !== "Extended") {
    tryDrop();
  }
}

function processManualControls() {
  currentGesture = "NONE";
  stableGesture = "NONE";
  actionGesture = "NONE";
  stableActionGesture = "NONE";
  pinching = false;
  showCursor = false;
  robotFrozen = false;

  if (manualKeys.KeyW && !manualKeys.KeyS) {
    stableGesture = "MOVE_FORWARD";
  } else if (manualKeys.KeyS && !manualKeys.KeyW) {
    stableGesture = "MOVE_BACKWARD";
  } else if (manualKeys.KeyA && !manualKeys.KeyD) {
    stableGesture = "MOVE_LEFT";
  } else if (manualKeys.KeyD && !manualKeys.KeyA) {
    stableGesture = "MOVE_RIGHT";
  }

  updateRobot();

  if (heldObject !== null && selectedPart("Arm (SPACE)") !== "Extended") {
    tryDrop();
  }
}

function drawMirroredVideoFrame() {
  detectionCtx.save();
  detectionCtx.clearRect(0, 0, CAM_W, CAM_H);
  detectionCtx.scale(-1, 1);
  detectionCtx.drawImage(video, -CAM_W, 0, CAM_W, CAM_H);
  detectionCtx.restore();
}

function loop(nowMs) {
  if (!running) {
    return;
  }

  frameSeconds = nowMs / 1000;

  const useHandTracking = controlMode === "gesture" && cameraAvailable && handTrackingAvailable && video.readyState >= 2;
  if (useHandTracking) {
    drawMirroredVideoFrame();

    let results = null;
    if (video.currentTime !== lastVideoTime) {
      results = handLandmarker.detectForVideo(detectionCanvas, nowMs);
      lastVideoTime = video.currentTime;
      lastDetectionResults = results;
    }

    processDetections(lastDetectionResults, nowMs);
  } else {
    processManualControls();
  }

  drawSim();
  drawModeBanner(ctx);

  if (robotFrozen) {
    drawFrozenLabel();
  }

  drawToolbox(ctx, cursorX, cursorY);
  drawStatusPanel(ctx);

  if (showCursor) {
    drawCursor();
  }

  drawPip();
  requestAnimationFrame(loop);
}

async function setupHandTracking() {
  if (!visionModule) {
    visionModule = await loadVisionModule();
  }
  const vision = await visionModule.FilesetResolver.forVisionTasks(activeWasmRoot);
  handLandmarker = await visionModule.HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: HAND_LANDMARKER_MODEL_URL
    },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.4,
    minTrackingConfidence: 0.4,
    minHandPresenceConfidence: 0.4
  });
}

async function setupCamera() {
  if (!window.isSecureContext) {
    throw new Error("Camera requires localhost or HTTPS. Manual keyboard mode is active");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Camera access is not supported in this browser");
  }

  mediaStream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: "user",
      width: { ideal: CAM_W },
      height: { ideal: CAM_H }
    },
    audio: false
  });

  video.srcObject = mediaStream;

  await new Promise((resolve, reject) => {
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error("Failed to load camera stream"));
  });

  await video.play();
}

async function init() {
  try {
    if (directOpenMode) {
      setControlMode("manual", "DIRECT OPEN MODE", "Opened from a local file. The robotic panel is ready");
      running = true;
      requestAnimationFrame(loop);
      return;
    }

    setBootScreen("INITIALIZING", "Loading MediaPipe");
    visionModule = await loadVisionModule();
    setBootScreen("INITIALIZING", "Loading hand tracking");
    await setupHandTracking();
    handTrackingAvailable = true;
    setBootScreen("INITIALIZING", "Opening camera");
    await setupCamera();
    cameraAvailable = true;
    setControlMode("gesture", "GESTURE MODE", "Camera and hand tracking are live");
    running = true;
    requestAnimationFrame(loop);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(error);
    setControlMode("manual", "MANUAL MODE", message);
    running = true;
    requestAnimationFrame(loop);
  }
}

window.addEventListener("keydown", (event) => {
  if (event.code in manualKeys) {
    manualKeys[event.code] = true;
  }

  if (controlMode === "manual" && event.key >= "1" && event.key <= "5") {
    event.preventDefault();
    cycleSelectedPart(TOOLBOX_CATEGORIES[Number(event.key) - 1]);
  }

  if (event.code === "Space") {
    event.preventDefault();
    if (heldObject === null) {
      tryPickup();
    } else {
      tryDrop();
    }
  }
  if (event.key === "q" || event.key === "Q" || event.key === "Escape") {
    event.preventDefault();
    stopApp();
  }
});

window.addEventListener("keyup", (event) => {
  if (event.code in manualKeys) {
    manualKeys[event.code] = false;
  }
});

window.addEventListener("beforeunload", () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
});

drawBootScreen();
init();
