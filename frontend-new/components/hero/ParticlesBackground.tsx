"use client";

import { useEffect, useRef, useCallback } from "react";

type ParticleShape =
  | "pulseRing"
  | "dataNode"
  | "scanLine"
  | "hexagon"
  | "crosshair"
  | "diamond"
  | "circuit"
  | "orb";

interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
  glowing: boolean;
  phase: number;
  shape: ParticleShape;
  rotation: number;
  rotationSpeed: number;
}

const SHAPES: ParticleShape[] = [
  "pulseRing", "dataNode", "scanLine", "hexagon",
  "crosshair", "diamond", "circuit", "orb"
];

// Pre-calculated constants
const PI2 = Math.PI * 2;
const PI_DIV_3 = Math.PI / 3;

function createParticle(width: number, height: number): Particle {
  const shapeIndex = Math.floor(Math.random() * SHAPES.length);
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 6 + 4,
    speedX: (Math.random() - 0.5) * 0.4,
    speedY: (Math.random() - 0.5) * 0.4,
    opacity: Math.random() * 0.3 + 0.1,
    glowing: Math.random() > 0.6,
    phase: Math.random() * PI2,
    shape: SHAPES[shapeIndex],
    rotation: Math.random() * PI2,
    rotationSpeed: (Math.random() - 0.5) * 0.015
  };
}

// Optimized draw function - reduced ctx state changes
function drawParticle(
  ctx: CanvasRenderingContext2D,
  particle: Particle,
  time: number,
  opacity: number
) {
  const s = particle.size;
  const pulse = Math.sin(time * 2 + particle.phase) * 0.3 + 0.7;

  ctx.save();
  ctx.translate(particle.x, particle.y);
  ctx.rotate(particle.rotation);

  const color = `rgba(16,240,160,${opacity})`;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1;

  switch (particle.shape) {
    case "pulseRing": {
      const ringSize = s * pulse;
      ctx.beginPath();
      ctx.arc(0, 0, ringSize, 0, PI2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.2, 0, PI2);
      ctx.fill();
      break;
    }

    case "dataNode": {
      const hs = s * 0.6;
      ctx.strokeRect(-hs, -hs, hs * 2, hs * 2);
      const sqProgress = ((time * 0.6 + particle.phase) % 4);
      const sqEdgeIndex = Math.floor(sqProgress);
      const sqEdgeProgress = sqProgress - sqEdgeIndex;
      // Inline vertex calculation
      const sqX = sqEdgeIndex === 0 ? -hs + (hs * 2) * sqEdgeProgress :
                  sqEdgeIndex === 1 ? hs :
                  sqEdgeIndex === 2 ? hs - (hs * 2) * sqEdgeProgress : -hs;
      const sqY = sqEdgeIndex === 0 ? -hs :
                  sqEdgeIndex === 1 ? -hs + (hs * 2) * sqEdgeProgress :
                  sqEdgeIndex === 2 ? hs : hs - (hs * 2) * sqEdgeProgress;
      ctx.beginPath();
      ctx.arc(sqX, sqY, s * 0.18 * pulse, 0, PI2);
      ctx.fill();
      break;
    }

    case "scanLine": {
      const lineWidth = s * 1.5;
      const scanPos = Math.sin(time * 3 + particle.phase) * lineWidth * 0.8;
      ctx.beginPath();
      ctx.moveTo(-lineWidth, 0);
      ctx.lineTo(lineWidth, 0);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(scanPos, 0, s * 0.2, 0, PI2);
      ctx.fill();
      break;
    }

    case "hexagon": {
      ctx.beginPath();
      const hexSize = s * pulse;
      ctx.moveTo(hexSize, 0);
      for (let i = 1; i < 6; i++) {
        const angle = i * PI_DIV_3;
        ctx.lineTo(Math.cos(angle) * hexSize, Math.sin(angle) * hexSize);
      }
      ctx.closePath();
      ctx.stroke();
      break;
    }

    case "crosshair": {
      const len = s * 0.8;
      const gap = s * 0.25;
      ctx.beginPath();
      ctx.moveTo(-len, 0);
      ctx.lineTo(-gap, 0);
      ctx.moveTo(gap, 0);
      ctx.lineTo(len, 0);
      ctx.moveTo(0, -len);
      ctx.lineTo(0, -gap);
      ctx.moveTo(0, gap);
      ctx.lineTo(0, len);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.12 * pulse, 0, PI2);
      ctx.fill();
      break;
    }

    case "diamond": {
      const d = s * 0.8;
      ctx.beginPath();
      ctx.moveTo(0, -d);
      ctx.lineTo(d, 0);
      ctx.lineTo(0, d);
      ctx.lineTo(-d, 0);
      ctx.closePath();
      ctx.stroke();
      const diaProgress = ((time * 0.55 + particle.phase) % 4);
      const diaEdgeIndex = Math.floor(diaProgress);
      const diaEdgeProgress = diaProgress - diaEdgeIndex;
      // Inline diamond vertex calculation
      const diaX = diaEdgeIndex === 0 ? d * diaEdgeProgress :
                   diaEdgeIndex === 1 ? d - d * diaEdgeProgress :
                   diaEdgeIndex === 2 ? -d * diaEdgeProgress : -d + d * diaEdgeProgress;
      const diaY = diaEdgeIndex === 0 ? -d + d * diaEdgeProgress :
                   diaEdgeIndex === 1 ? d * diaEdgeProgress :
                   diaEdgeIndex === 2 ? d - d * diaEdgeProgress : -d * diaEdgeProgress;
      ctx.beginPath();
      ctx.arc(diaX, diaY, s * 0.18 * pulse, 0, PI2);
      ctx.fill();
      break;
    }

    case "circuit": {
      const ts = s * 0.8;
      const tsH = ts * 0.866;
      const tsV = ts * 0.5;
      ctx.beginPath();
      ctx.moveTo(0, -ts);
      ctx.lineTo(tsH, tsV);
      ctx.lineTo(-tsH, tsV);
      ctx.closePath();
      ctx.stroke();
      const triProgress = ((time * 0.5 + particle.phase) % 3);
      const edgeIndex = Math.floor(triProgress);
      const edgeProgress = triProgress - edgeIndex;
      // Inline triangle vertex calculation
      let dotX: number, dotY: number;
      if (edgeIndex === 0) {
        dotX = tsH * edgeProgress;
        dotY = -ts + (tsV + ts) * edgeProgress;
      } else if (edgeIndex === 1) {
        dotX = tsH - (tsH * 2) * edgeProgress;
        dotY = tsV;
      } else {
        dotX = -tsH + tsH * edgeProgress;
        dotY = tsV - (tsV + ts) * edgeProgress;
      }
      ctx.beginPath();
      ctx.arc(dotX, dotY, s * 0.2 * pulse, 0, PI2);
      ctx.fill();
      break;
    }

    case "orb": {
      const orbPulse = 0.7 + Math.sin(time * 2.5 + particle.phase) * 0.3;
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.9, 0, PI2);
      ctx.stroke();
      ctx.globalAlpha = opacity * 0.4 * orbPulse;
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.5 * orbPulse, 0, PI2);
      ctx.fill();
      break;
    }
  }

  ctx.restore();
}

export function ParticlesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>(0);
  const isVisibleRef = useRef(true);
  const isMobileRef = useRef(false);

  // Mouse state refs
  const mousePosRef = useRef({ x: -1000, y: -1000 });
  const mouseVelocityRef = useRef({ x: 0, y: 0 });
  const lastMouseTimeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    // Detect mobile
    isMobileRef.current = window.innerWidth < 768 || 'ontouchstart' in window;

    let width = window.innerWidth;
    let height = window.innerHeight;

    const resizeCanvas = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2); // Cap DPR at 2 for performance
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      isMobileRef.current = width < 768 || 'ontouchstart' in window;
    };
    resizeCanvas();

    // Reduce particle count on mobile
    const baseCount = isMobileRef.current ? 25 : 35;
    const maxCount = isMobileRef.current ? 50 : 80;
    const targetParticleCount = Math.min(maxCount, Math.max(baseCount, Math.floor(width / (isMobileRef.current ? 30 : 20))));
    const initialParticleCount = isMobileRef.current ? 3 : 5;

    particlesRef.current = Array.from({ length: initialParticleCount }, () =>
      createParticle(width, height)
    );

    // Gradually spawn particles
    let spawnedCount = initialParticleCount;
    const spawnInterval = setInterval(() => {
      if (spawnedCount >= targetParticleCount) {
        clearInterval(spawnInterval);
        return;
      }
      const toSpawn = Math.min(isMobileRef.current ? 2 : 3, targetParticleCount - spawnedCount);
      for (let i = 0; i < toSpawn; i++) {
        particlesRef.current.push(createParticle(width, height));
      }
      spawnedCount += toSpawn;
    }, isMobileRef.current ? 100 : 80);

    // Visibility detection - pause animation when not visible
    // rootMargin extends the detection area so animation continues while particles are still visible
    const observer = new IntersectionObserver(
      (entries) => {
        isVisibleRef.current = entries[0]?.isIntersecting ?? true;
      },
      { threshold: 0, rootMargin: "200px 0px 200px 0px" }
    );
    observer.observe(canvas);

    // Throttled resize handler
    let resizeTimeout: ReturnType<typeof setTimeout>;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        resizeCanvas();
        const newMax = isMobileRef.current ? 50 : 80;
        const newBase = isMobileRef.current ? 25 : 35;
        const newCount = Math.min(newMax, Math.max(newBase, Math.floor(width / (isMobileRef.current ? 30 : 20))));
        const currentCount = particlesRef.current.length;

        if (newCount > currentCount) {
          for (let i = currentCount; i < newCount; i++) {
            particlesRef.current.push(createParticle(width, height));
          }
        } else if (newCount < currentCount) {
          particlesRef.current.length = newCount;
        }
      }, 150);
    };

    // Throttled mouse handler - only update every 16ms (~60fps)
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

    // Animation loop with visibility check
    let lastTime = 0;
    const targetFPS = isMobileRef.current ? 30 : 60;
    const frameInterval = 1000 / targetFPS;

    const animate = (currentTime: number) => {
      animationRef.current = requestAnimationFrame(animate);

      // Skip if not visible
      if (!isVisibleRef.current) return;

      // Frame rate limiting for mobile
      if (isMobileRef.current) {
        const deltaTime = currentTime - lastTime;
        if (deltaTime < frameInterval) return;
        lastTime = currentTime - (deltaTime % frameInterval);
      }

      ctx.clearRect(0, 0, width, height);
      const time = currentTime * 0.001;
      const mousePos = mousePosRef.current;
      const mouseVel = mouseVelocityRef.current;

      // Calculate mouse speed (avoid sqrt when possible)
      const mouseSpeedSq = mouseVel.x * mouseVel.x + mouseVel.y * mouseVel.y;
      const mouseSpeed = mouseSpeedSq > 0 ? Math.sqrt(mouseSpeedSq) : 0;
      const effectRadius = Math.min(180, 80 + mouseSpeed * 3);
      const effectRadiusSq = effectRadius * effectRadius;

      // Decay mouse velocity
      mouseVel.x *= 0.92;
      mouseVel.y *= 0.92;

      const particles = particlesRef.current;
      const len = particles.length;

      for (let i = 0; i < len; i++) {
        const particle = particles[i];

        // Distance from mouse (squared first to avoid sqrt)
        const dx = particle.x - mousePos.x;
        const dy = particle.y - mousePos.y;
        const distanceSq = dx * dx + dy * dy;

        if (distanceSq < effectRadiusSq && distanceSq > 0) {
          const distance = Math.sqrt(distanceSq);
          const normalizedDist = distance / effectRadius;
          const force = (1 - normalizedDist) * (1 - normalizedDist) * 0.9;

          const pushAngle = Math.atan2(dy, dx);
          const swirlAngle = pushAngle + Math.PI * 0.5;
          const swirlStrength = mouseSpeed * force * 0.08;
          const swirlInfluence = Math.min(mouseSpeed * 0.04, 1.2);

          particle.x += Math.cos(pushAngle) * force * 2.0 +
                        mouseVel.x * force * 0.18 +
                        Math.cos(swirlAngle) * swirlStrength * swirlInfluence;
          particle.y += Math.sin(pushAngle) * force * 2.0 +
                        mouseVel.y * force * 0.18 +
                        Math.sin(swirlAngle) * swirlStrength * swirlInfluence;

          const crossProduct = dx * mouseVel.y - dy * mouseVel.x;
          particle.rotationSpeed += force * mouseSpeed * 0.006 * (crossProduct > 0 ? 1 : -1);
          particle.speedX += Math.cos(swirlAngle) * force * mouseSpeed * 0.003;
          particle.speedY += Math.sin(swirlAngle) * force * mouseSpeed * 0.003;
        }

        // Physics update
        particle.rotationSpeed *= 0.96;
        particle.speedX *= 0.995;
        particle.speedY *= 0.995;

        // Restore base drift occasionally
        if (Math.abs(particle.speedX) < 0.1 && Math.random() < 0.1) {
          particle.speedX += (Math.random() - 0.5) * 0.02;
        }
        if (Math.abs(particle.speedY) < 0.1 && Math.random() < 0.1) {
          particle.speedY += (Math.random() - 0.5) * 0.02;
        }

        particle.x += particle.speedX;
        particle.y += particle.speedY;
        particle.rotation += particle.rotationSpeed;

        // Edge wrapping
        if (particle.x < -20) particle.x = width + 20;
        else if (particle.x > width + 20) particle.x = -20;
        if (particle.y < -20) particle.y = height + 20;
        else if (particle.y > height + 20) particle.y = -20;

        // Calculate opacity
        let drawOpacity = particle.opacity;
        if (particle.glowing) {
          drawOpacity += Math.sin(time * 1.5 + particle.phase) * 0.12 + 0.12;
        }

        // Glow effect (skip on mobile for performance)
        if (particle.glowing && !isMobileRef.current) {
          ctx.shadowBlur = 12;
          ctx.shadowColor = `rgba(16,240,160,${drawOpacity * 0.8})`;
        }

        drawParticle(ctx, particle, time, drawOpacity);

        if (particle.glowing && !isMobileRef.current) {
          ctx.shadowBlur = 0;
        }
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
