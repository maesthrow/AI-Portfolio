"use client";

import { useEffect, useRef } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Neuron {
  x: number;
  y: number;
  baseRadius: number;
  activation: number;
  baseActivation: number;
  speedX: number;
  speedY: number;
  phase: number;
  layer: number; // 0 = far, 1 = mid, 2 = near
  connections: number[];
}

interface Signal {
  fromIdx: number;
  toIdx: number;
  progress: number; // 0-1 along the connection
  speed: number;
  active: boolean;
  isPurple: boolean;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const PI2 = Math.PI * 2;

const CONFIG = {
  desktop: {
    baseCount: 88,
    maxCount: 200,
    maxConnDist: 180,
    maxConnsPerNeuron: 5,
    connRebuildInterval: 60,
    maxSignals: 31,
    signalSpawnInterval: 48,
    fps: 60,
    glowEnabled: true,
    mouseEffectRadius: 160,
    divisor: 10,
  },
  mobile: {
    baseCount: 50,
    maxCount: 100,
    maxConnDist: 120,
    maxConnsPerNeuron: 3,
    connRebuildInterval: 90,
    maxSignals: 15,
    signalSpawnInterval: 80,
    fps: 30,
    glowEnabled: false,
    mouseEffectRadius: 100,
    divisor: 16,
  },
} as const;

const LAYER_CONFIGS = [
  { speedMult: 0.7, opacityMult: 0.5, sizeMult: 0.8 },
  { speedMult: 1.0, opacityMult: 0.75, sizeMult: 1.0 },
  { speedMult: 1.3, opacityMult: 1.0, sizeMult: 1.15 },
];

const COLOR_GREEN = { r: 16, g: 240, b: 160 };
const COLOR_PURPLE = { r: 139, g: 92, b: 246 };

/* ------------------------------------------------------------------ */
/*  Neuron creation                                                    */
/* ------------------------------------------------------------------ */

function createNeuron(width: number, height: number): Neuron {
  const isHub = Math.random() < 0.15;
  const layerRoll = Math.random();
  const layer = layerRoll < 0.3 ? 0 : layerRoll < 0.75 ? 1 : 2;
  const layerCfg = LAYER_CONFIGS[layer];

  return {
    x: Math.random() * width,
    y: Math.random() * height,
    baseRadius:
      (isHub ? Math.random() * 3 + 5 : Math.random() * 3 + 2) *
      layerCfg.sizeMult,
    activation: Math.random() * 0.15 + 0.1,
    baseActivation: Math.random() * 0.2 + 0.1,
    speedX: (Math.random() - 0.5) * 0.4 * layerCfg.speedMult,
    speedY: (Math.random() - 0.5) * 0.4 * layerCfg.speedMult,
    phase: Math.random() * PI2,
    layer,
    connections: [],
  };
}

/* ------------------------------------------------------------------ */
/*  Connection topology                                                */
/* ------------------------------------------------------------------ */

function rebuildConnections(
  neurons: Neuron[],
  maxDist: number,
  maxPerNeuron: number,
): void {
  const len = neurons.length;
  const maxDistSq = maxDist * maxDist;

  for (let i = 0; i < len; i++) {
    neurons[i].connections.length = 0;
  }

  for (let i = 0; i < len; i++) {
    if (neurons[i].connections.length >= maxPerNeuron) continue;

    const candidates: Array<{ idx: number; distSq: number }> = [];

    for (let j = i + 1; j < len; j++) {
      if (neurons[j].connections.length >= maxPerNeuron) continue;
      const dx = neurons[i].x - neurons[j].x;
      const dy = neurons[i].y - neurons[j].y;
      const distSq = dx * dx + dy * dy;
      if (distSq < maxDistSq) {
        candidates.push({ idx: j, distSq });
      }
    }

    candidates.sort((a, b) => a.distSq - b.distSq);
    const slotsAvailable = maxPerNeuron - neurons[i].connections.length;
    const toConnect = Math.min(slotsAvailable, candidates.length);

    for (let k = 0; k < toConnect; k++) {
      const j = candidates[k].idx;
      if (neurons[j].connections.length >= maxPerNeuron) continue;
      neurons[i].connections.push(j);
      neurons[j].connections.push(i);
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Drawing helpers                                                    */
/* ------------------------------------------------------------------ */

function drawNeuron(
  ctx: CanvasRenderingContext2D,
  neuron: Neuron,
  time: number,
  glowEnabled: boolean,
): void {
  const layerCfg = LAYER_CONFIGS[neuron.layer];
  const { activation } = neuron;

  const breathe = 1 + Math.sin(time * 1.8 + neuron.phase) * 0.08;
  const radius = neuron.baseRadius * breathe;

  const baseOpacity = 0.15 * layerCfg.opacityMult;
  const activationOpacity = activation * 0.7 * layerCfg.opacityMult;
  const totalOpacity = baseOpacity + activationOpacity;

  const { r, g, b } = COLOR_GREEN;

  // Outer glow halo (desktop only, when activated)
  if (glowEnabled && activation > 0.2) {
    const glowRadius = radius * (2.0 + activation * 1.5);
    const glowOpacity = activation * 0.12 * layerCfg.opacityMult;
    ctx.beginPath();
    ctx.arc(neuron.x, neuron.y, glowRadius, 0, PI2);
    ctx.fillStyle = `rgba(${r},${g},${b},${glowOpacity})`;
    ctx.fill();
  }

  // Outer ring ("membrane")
  ctx.beginPath();
  ctx.arc(neuron.x, neuron.y, radius * 1.6, 0, PI2);
  ctx.strokeStyle = `rgba(${r},${g},${b},${totalOpacity * 0.4})`;
  ctx.lineWidth = 0.5;
  ctx.stroke();

  // Inner core
  ctx.beginPath();
  ctx.arc(neuron.x, neuron.y, radius * 0.6, 0, PI2);
  ctx.fillStyle = `rgba(${r},${g},${b},${totalOpacity})`;
  ctx.fill();

  // Bright center dot when activated
  if (activation > 0.3) {
    const dotOpacity = Math.min(1, activation * 1.2) * layerCfg.opacityMult;
    ctx.beginPath();
    ctx.arc(neuron.x, neuron.y, radius * 0.25, 0, PI2);
    ctx.fillStyle = `rgba(${r},${g},${b},${dotOpacity})`;
    ctx.fill();
  }
}

function drawConnection(
  ctx: CanvasRenderingContext2D,
  n1: Neuron,
  n2: Neuron,
  maxDist: number,
): void {
  const dx = n2.x - n1.x;
  const dy = n2.y - n1.y;
  const distSq = dx * dx + dy * dy;
  const maxDistSq = maxDist * maxDist;
  if (distSq > maxDistSq) return;

  const dist = Math.sqrt(distSq);
  const distFactor = 1 - dist / maxDist;
  const activationFactor = (n1.activation + n2.activation) * 0.5;
  const opacity = distFactor * (0.04 + activationFactor * 0.12);
  const layerMult =
    (LAYER_CONFIGS[n1.layer].opacityMult +
      LAYER_CONFIGS[n2.layer].opacityMult) *
    0.5;

  const { r, g, b } = COLOR_GREEN;

  ctx.beginPath();
  ctx.moveTo(n1.x, n1.y);
  ctx.lineTo(n2.x, n2.y);
  ctx.strokeStyle = `rgba(${r},${g},${b},${opacity * layerMult})`;
  ctx.lineWidth = 0.5 + activationFactor * 0.5;
  ctx.stroke();
}

function drawSignal(
  ctx: CanvasRenderingContext2D,
  signal: Signal,
  neurons: Neuron[],
): void {
  const from = neurons[signal.fromIdx];
  const to = neurons[signal.toIdx];

  const x = from.x + (to.x - from.x) * signal.progress;
  const y = from.y + (to.y - from.y) * signal.progress;

  const edgeFade = 1 - Math.abs(signal.progress - 0.5) * 2;
  const brightness = 0.6 + edgeFade * 0.4;

  const color = signal.isPurple ? COLOR_PURPLE : COLOR_GREEN;
  const { r, g, b } = color;

  // Glow halo
  ctx.beginPath();
  ctx.arc(x, y, 6, 0, PI2);
  ctx.fillStyle = `rgba(${r},${g},${b},${brightness * 0.15})`;
  ctx.fill();

  // Core dot
  ctx.beginPath();
  ctx.arc(x, y, 2.5, 0, PI2);
  ctx.fillStyle = `rgba(${r},${g},${b},${brightness * 0.9})`;
  ctx.fill();

  // Bright center
  ctx.beginPath();
  ctx.arc(x, y, 1, 0, PI2);
  ctx.fillStyle = `rgba(${r},${g},${b},${brightness})`;
  ctx.fill();
}

/* ------------------------------------------------------------------ */
/*  Signal management                                                  */
/* ------------------------------------------------------------------ */

function spawnSignal(
  signals: Signal[],
  fromIdx: number,
  neurons: Neuron[],
  maxSignals: number,
): void {
  const from = neurons[fromIdx];
  if (from.connections.length === 0) return;

  const toIdx =
    from.connections[Math.floor(Math.random() * from.connections.length)];

  // Find inactive slot
  let slot = -1;
  for (let i = 0; i < signals.length; i++) {
    if (!signals[i].active) {
      slot = i;
      break;
    }
  }

  if (slot === -1) {
    if (signals.length >= maxSignals) return;
    slot = signals.length;
    signals.push({
      fromIdx: 0,
      toIdx: 0,
      progress: 0,
      speed: 0,
      active: false,
      isPurple: false,
    });
  }

  signals[slot].fromIdx = fromIdx;
  signals[slot].toIdx = toIdx;
  signals[slot].progress = 0;
  signals[slot].speed = 0.015 + Math.random() * 0.01;
  signals[slot].active = true;
  signals[slot].isPurple = Math.random() < 0.2;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ParticlesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const neuronsRef = useRef<Neuron[]>([]);
  const signalsRef = useRef<Signal[]>([]);
  const animationRef = useRef<number>(0);
  const isVisibleRef = useRef(true);
  const isMobileRef = useRef(false);

  const mousePosRef = useRef({ x: -1000, y: -1000 });
  const mouseVelocityRef = useRef({ x: 0, y: 0 });
  const lastMouseTimeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    isMobileRef.current =
      window.innerWidth < 768 || "ontouchstart" in window;

    let width = window.innerWidth;
    let height = window.innerHeight;

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      isMobileRef.current = width < 768 || "ontouchstart" in window;
    };
    resizeCanvas();

    const cfg = isMobileRef.current ? CONFIG.mobile : CONFIG.desktop;
    const targetCount = Math.min(
      cfg.maxCount,
      Math.max(cfg.baseCount, Math.floor(width / cfg.divisor)),
    );
    const initialCount = isMobileRef.current ? 3 : 5;

    neuronsRef.current = Array.from({ length: initialCount }, () =>
      createNeuron(width, height),
    );
    signalsRef.current = [];

    // Gradually spawn neurons
    let spawnedCount = initialCount;
    const spawnInterval = setInterval(() => {
      if (spawnedCount >= targetCount) {
        clearInterval(spawnInterval);
        rebuildConnections(
          neuronsRef.current,
          cfg.maxConnDist,
          cfg.maxConnsPerNeuron,
        );
        return;
      }
      const toSpawn = Math.min(
        isMobileRef.current ? 2 : 3,
        targetCount - spawnedCount,
      );
      for (let i = 0; i < toSpawn; i++) {
        neuronsRef.current.push(createNeuron(width, height));
      }
      spawnedCount += toSpawn;
    }, isMobileRef.current ? 100 : 80);

    // Visibility detection
    const observer = new IntersectionObserver(
      (entries) => {
        isVisibleRef.current = entries[0]?.isIntersecting ?? true;
      },
      { threshold: 0, rootMargin: "200px 0px 200px 0px" },
    );
    observer.observe(canvas);

    // Throttled resize
    let resizeTimeout: ReturnType<typeof setTimeout>;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        resizeCanvas();
        const newCfg = isMobileRef.current ? CONFIG.mobile : CONFIG.desktop;
        const newCount = Math.min(
          newCfg.maxCount,
          Math.max(
            newCfg.baseCount,
            Math.floor(width / newCfg.divisor),
          ),
        );
        const currentCount = neuronsRef.current.length;

        if (newCount > currentCount) {
          for (let i = currentCount; i < newCount; i++) {
            neuronsRef.current.push(createNeuron(width, height));
          }
        } else if (newCount < currentCount) {
          const signals = signalsRef.current;
          for (let i = 0; i < signals.length; i++) {
            if (
              signals[i].active &&
              (signals[i].fromIdx >= newCount ||
                signals[i].toIdx >= newCount)
            ) {
              signals[i].active = false;
            }
          }
          neuronsRef.current.length = newCount;
        }

        rebuildConnections(
          neuronsRef.current,
          newCfg.maxConnDist,
          newCfg.maxConnsPerNeuron,
        );
      }, 150);
    };

    // Mouse tracking
    const handleMouseMove = (e: MouseEvent) => {
      const now = performance.now();
      if (now - lastMouseTimeRef.current < 16) return;
      lastMouseTimeRef.current = now;

      const prev = mousePosRef.current;
      const newX = e.clientX;
      const newY = e.clientY;

      if (prev.x > -500) {
        mouseVelocityRef.current.x = newX - prev.x;
        mouseVelocityRef.current.y = newY - prev.y;
      }

      mousePosRef.current.x = newX;
      mousePosRef.current.y = newY;
    };

    window.addEventListener("resize", handleResize, { passive: true });
    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    // Animation loop
    let lastTime = 0;
    let frameCount = 0;
    const frameInterval = 1000 / cfg.fps;

    const animate = (currentTime: number) => {
      animationRef.current = requestAnimationFrame(animate);

      if (!isVisibleRef.current) return;

      if (isMobileRef.current) {
        const deltaTime = currentTime - lastTime;
        if (deltaTime < frameInterval) return;
        lastTime = currentTime - (deltaTime % frameInterval);
      }

      frameCount++;
      ctx.clearRect(0, 0, width, height);
      const time = currentTime * 0.001;
      const mousePos = mousePosRef.current;
      const mouseVel = mouseVelocityRef.current;
      const isMobile = isMobileRef.current;

      const effectRadius = cfg.mouseEffectRadius;
      const effectRadiusSq = effectRadius * effectRadius;

      mouseVel.x *= 0.92;
      mouseVel.y *= 0.92;

      const neurons = neuronsRef.current;
      const signals = signalsRef.current;
      const len = neurons.length;

      // Periodic connection rebuild
      if (frameCount % cfg.connRebuildInterval === 0 && len > 1) {
        rebuildConnections(neurons, cfg.maxConnDist, cfg.maxConnsPerNeuron);
      }

      // Random signal spawn
      if (frameCount % cfg.signalSpawnInterval === 0 && len > 1) {
        const randomIdx = Math.floor(Math.random() * len);
        spawnSignal(signals, randomIdx, neurons, cfg.maxSignals);
      }

      // Update neurons
      for (let i = 0; i < len; i++) {
        const neuron = neurons[i];

        // Activation decay
        neuron.activation = Math.max(
          neuron.baseActivation,
          neuron.activation * 0.97,
        );

        // Mouse interaction
        const dx = neuron.x - mousePos.x;
        const dy = neuron.y - mousePos.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < effectRadiusSq && distSq > 0) {
          const distance = Math.sqrt(distSq);
          const normalizedDist = distance / effectRadius;
          const force = (1 - normalizedDist) * (1 - normalizedDist);

          const pushAngle = Math.atan2(dy, dx);
          neuron.x += Math.cos(pushAngle) * force * 1.2;
          neuron.y += Math.sin(pushAngle) * force * 1.2;

          neuron.activation = Math.min(
            1.0,
            neuron.activation + force * 0.4,
          );

          if (neuron.activation > 0.6 && Math.random() < 0.02) {
            spawnSignal(signals, i, neurons, cfg.maxSignals);
          }
        }

        // Physics
        neuron.speedX *= 0.995;
        neuron.speedY *= 0.995;

        if (Math.abs(neuron.speedX) < 0.05 && Math.random() < 0.05) {
          neuron.speedX += (Math.random() - 0.5) * 0.02;
        }
        if (Math.abs(neuron.speedY) < 0.05 && Math.random() < 0.05) {
          neuron.speedY += (Math.random() - 0.5) * 0.02;
        }

        neuron.x += neuron.speedX;
        neuron.y += neuron.speedY;

        // Edge wrapping
        if (neuron.x < -20) neuron.x = width + 20;
        else if (neuron.x > width + 20) neuron.x = -20;
        if (neuron.y < -20) neuron.y = height + 20;
        else if (neuron.y > height + 20) neuron.y = -20;
      }

      // Update signals
      for (let i = 0; i < signals.length; i++) {
        const signal = signals[i];
        if (!signal.active) continue;

        signal.progress += signal.speed;

        if (signal.progress >= 1.0) {
          signal.active = false;
          const target = neurons[signal.toIdx];
          if (target) {
            target.activation = Math.min(1.0, target.activation + 0.4);

            if (target.activation > 0.5 && Math.random() < 0.5) {
              spawnSignal(signals, signal.toIdx, neurons, cfg.maxSignals);
            }
          }
        }
      }

      // Draw connections (back layer)
      const drawnPairs = new Set<number>();
      for (let i = 0; i < len; i++) {
        const conns = neurons[i].connections;
        for (let c = 0; c < conns.length; c++) {
          const j = conns[c];
          const pairKey = i < j ? i * 1000 + j : j * 1000 + i;
          if (drawnPairs.has(pairKey)) continue;
          drawnPairs.add(pairKey);
          drawConnection(ctx, neurons[i], neurons[j], cfg.maxConnDist);
        }
      }

      // Draw signals (mid layer)
      for (let i = 0; i < signals.length; i++) {
        if (signals[i].active) {
          drawSignal(ctx, signals[i], neurons);
        }
      }

      // Draw neurons (front layer)
      for (let i = 0; i < len; i++) {
        drawNeuron(ctx, neurons[i], time, !isMobile && cfg.glowEnabled);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      clearInterval(spawnInterval);
      clearTimeout(resizeTimeout);
      observer.disconnect();
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(animationRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0"
      aria-hidden="true"
    />
  );
}
