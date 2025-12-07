"use client";

import { useEffect, useRef } from "react";

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

function createParticle(width: number, height: number): Particle {
  const shapeIndex = Math.floor(Math.random() * SHAPES.length);
  const shape = SHAPES[shapeIndex];
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 6 + 4,
    speedX: (Math.random() - 0.5) * 0.4,
    speedY: (Math.random() - 0.5) * 0.4,
    opacity: Math.random() * 0.3 + 0.1,
    glowing: Math.random() > 0.6,
    phase: Math.random() * Math.PI * 2,
    shape,
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.015
  };
}

function drawParticle(
  ctx: CanvasRenderingContext2D,
  particle: Particle,
  color: string,
  time: number
) {
  ctx.save();
  ctx.translate(particle.x, particle.y);
  ctx.rotate(particle.rotation);

  const s = particle.size;
  const pulse = Math.sin(time * 2 + particle.phase) * 0.3 + 0.7;

  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1;

  switch (particle.shape) {
    case "pulseRing": {
      // Пульсирующее кольцо с внутренней точкой
      const ringSize = s * pulse;
      ctx.beginPath();
      ctx.arc(0, 0, ringSize, 0, Math.PI * 2);
      ctx.stroke();
      // Внутренняя точка
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.2, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "dataNode": {
      // Квадрат с точкой, бегающей по рёбрам
      const hs = s * 0.6;
      ctx.strokeRect(-hs, -hs, hs * 2, hs * 2);
      // Вершины квадрата (по часовой стрелке)
      const sqPoints = [
        { x: -hs, y: -hs },
        { x: hs, y: -hs },
        { x: hs, y: hs },
        { x: -hs, y: hs }
      ];
      // Точка бегает по периметру (0-4 = полный цикл по 4 рёбрам)
      const sqProgress = ((time * 0.6 + particle.phase) % 4);
      const sqEdgeIndex = Math.floor(sqProgress);
      const sqEdgeProgress = sqProgress - sqEdgeIndex;
      const sq1 = sqPoints[sqEdgeIndex];
      const sq2 = sqPoints[(sqEdgeIndex + 1) % 4];
      const sqDotX = sq1.x + (sq2.x - sq1.x) * sqEdgeProgress;
      const sqDotY = sq1.y + (sq2.y - sq1.y) * sqEdgeProgress;
      ctx.beginPath();
      ctx.arc(sqDotX, sqDotY, s * 0.18 * pulse, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "scanLine": {
      // Горизонтальная линия со "сканирующим" эффектом
      const lineWidth = s * 1.5;
      const scanPos = Math.sin(time * 3 + particle.phase) * lineWidth * 0.8;
      ctx.beginPath();
      ctx.moveTo(-lineWidth, 0);
      ctx.lineTo(lineWidth, 0);
      ctx.stroke();
      // Яркая точка "сканера"
      ctx.beginPath();
      ctx.arc(scanPos, 0, s * 0.2, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "hexagon": {
      // Шестиугольник
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const angle = (i * Math.PI) / 3;
        const x = Math.cos(angle) * s * pulse;
        const y = Math.sin(angle) * s * pulse;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
      break;
    }

    case "crosshair": {
      // Прицел
      const len = s * 0.8;
      const gap = s * 0.25;
      // Линии
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
      // Центральная точка пульсирует
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.12 * pulse, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "diamond": {
      // Ромб с точкой, бегающей по рёбрам
      const d = s * 0.8;
      // Вершины ромба
      const diamondPoints = [
        { x: 0, y: -d },
        { x: d, y: 0 },
        { x: 0, y: d },
        { x: -d, y: 0 }
      ];
      ctx.beginPath();
      ctx.moveTo(diamondPoints[0].x, diamondPoints[0].y);
      ctx.lineTo(diamondPoints[1].x, diamondPoints[1].y);
      ctx.lineTo(diamondPoints[2].x, diamondPoints[2].y);
      ctx.lineTo(diamondPoints[3].x, diamondPoints[3].y);
      ctx.closePath();
      ctx.stroke();
      // Точка бегает по периметру (0-4 = полный цикл по 4 рёбрам)
      const diaProgress = ((time * 0.55 + particle.phase) % 4);
      const diaEdgeIndex = Math.floor(diaProgress);
      const diaEdgeProgress = diaProgress - diaEdgeIndex;
      const dia1 = diamondPoints[diaEdgeIndex];
      const dia2 = diamondPoints[(diaEdgeIndex + 1) % 4];
      const diaDotX = dia1.x + (dia2.x - dia1.x) * diaEdgeProgress;
      const diaDotY = dia1.y + (dia2.y - dia1.y) * diaEdgeProgress;
      ctx.beginPath();
      ctx.arc(diaDotX, diaDotY, s * 0.18 * pulse, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "circuit": {
      // Треугольник с точкой, бегающей по рёбрам
      const ts = s * 0.8;
      // Вершины треугольника
      const triPoints = [
        { x: 0, y: -ts },
        { x: ts * 0.866, y: ts * 0.5 },
        { x: -ts * 0.866, y: ts * 0.5 }
      ];
      ctx.beginPath();
      ctx.moveTo(triPoints[0].x, triPoints[0].y);
      ctx.lineTo(triPoints[1].x, triPoints[1].y);
      ctx.lineTo(triPoints[2].x, triPoints[2].y);
      ctx.closePath();
      ctx.stroke();
      // Точка бегает по периметру (0-3 = полный цикл по 3 рёбрам)
      const triProgress = ((time * 0.5 + particle.phase) % 3);
      const edgeIndex = Math.floor(triProgress);
      const edgeProgress = triProgress - edgeIndex;
      const p1 = triPoints[edgeIndex];
      const p2 = triPoints[(edgeIndex + 1) % 3];
      const dotX = p1.x + (p2.x - p1.x) * edgeProgress;
      const dotY = p1.y + (p2.y - p1.y) * edgeProgress;
      ctx.beginPath();
      ctx.arc(dotX, dotY, s * 0.2 * pulse, 0, Math.PI * 2);
      ctx.fill();
      break;
    }

    case "orb": {
      // Светящаяся сфера с кольцом
      const orbPulse = 0.7 + Math.sin(time * 2.5 + particle.phase) * 0.3;
      // Внешнее кольцо
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.9, 0, Math.PI * 2);
      ctx.stroke();
      // Внутренняя заливка
      ctx.globalAlpha = 0.4 * orbPulse;
      ctx.beginPath();
      ctx.arc(0, 0, s * 0.5 * orbPulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      break;
    }
  }

  ctx.restore();
}

export function ParticlesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>(0);
  const mousePosRef = useRef({ x: -1000, y: -1000 });
  const mouseVelocityRef = useRef({ x: 0, y: 0 });
  const resizeRafRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (prefersReducedMotion) {
      return;
    }

    let width = window.innerWidth;
    let height = window.innerHeight;

    const resizeCanvas = () => {
      const dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resizeCanvas();

    const targetParticleCount = Math.min(80, Math.max(35, Math.floor(width / 20)));
    const initialParticleCount = 5;
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
      const toSpawn = Math.min(3, targetParticleCount - spawnedCount);
      for (let i = 0; i < toSpawn; i++) {
        particlesRef.current.push(createParticle(width, height));
      }
      spawnedCount += toSpawn;
    }, 80);

    const updateParticleCount = () => {
      resizeCanvas();
      const newCount = Math.min(80, Math.max(35, Math.floor(width / 20)));
      const currentCount = particlesRef.current.length;

      if (newCount > currentCount) {
        for (let i = currentCount; i < newCount; i++) {
          particlesRef.current.push(createParticle(width, height));
        }
      } else if (newCount < currentCount) {
        particlesRef.current = particlesRef.current.slice(0, newCount);
      }
    };

    const handleResize = () => {
      if (resizeRafRef.current) return;
      resizeRafRef.current = requestAnimationFrame(() => {
        resizeRafRef.current = null;
        updateParticleCount();
      });
    };

    const handleMouseMove = (e: MouseEvent) => {
      const newPos = { x: e.clientX, y: e.clientY };
      const prev = mousePosRef.current;

      // Calculate velocity based on mouse movement
      if (prev.x > -500) {
        mouseVelocityRef.current = {
          x: newPos.x - prev.x,
          y: newPos.y - prev.y
        };
      }

      mousePosRef.current = newPos;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      const time = Date.now() * 0.001;
      const mousePos = mousePosRef.current;
      const mouseVel = mouseVelocityRef.current;

      // Calculate mouse speed for dynamic effect radius
      const mouseSpeed = Math.sqrt(mouseVel.x * mouseVel.x + mouseVel.y * mouseVel.y);
      const effectRadius = Math.min(180, 80 + mouseSpeed * 3);

      // Decay mouse velocity over time for smoother effect
      mouseVelocityRef.current = {
        x: mouseVel.x * 0.92,
        y: mouseVel.y * 0.92
      };

      const baseSpeed = 0.2;
      const minSpeed = baseSpeed * 0.5;

      particlesRef.current.forEach((particle) => {
        // Distance from mouse
        const dx = particle.x - mousePos.x;
        const dy = particle.y - mousePos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < effectRadius && distance > 0) {
          // Non-linear force falloff (stronger close, gentler far)
          const normalizedDist = distance / effectRadius;
          const force = Math.pow(1 - normalizedDist, 1.5) * 0.9;

          // Direction from mouse to particle
          const pushAngle = Math.atan2(dy, dx);

          // Calculate perpendicular angle for swirl effect
          const swirlAngle = pushAngle + Math.PI * 0.5;

          // Swirl strength based on mouse speed and proximity
          const swirlStrength = mouseSpeed * force * 0.08;

          // Combine: radial push + velocity direction + perpendicular swirl
          const radialPush = 2.0;
          const velocityInfluence = 0.18;
          const swirlInfluence = Math.min(mouseSpeed * 0.04, 1.2);

          const pushX =
            Math.cos(pushAngle) * force * radialPush +
            mouseVel.x * force * velocityInfluence +
            Math.cos(swirlAngle) * swirlStrength * swirlInfluence;
          const pushY =
            Math.sin(pushAngle) * force * radialPush +
            mouseVel.y * force * velocityInfluence +
            Math.sin(swirlAngle) * swirlStrength * swirlInfluence;

          particle.x += pushX;
          particle.y += pushY;

          // Enhanced spin - direction based on which side of mouse movement
          const crossProduct = dx * mouseVel.y - dy * mouseVel.x;
          const spinDirection = crossProduct > 0 ? 1 : -1;
          particle.rotationSpeed += force * mouseSpeed * 0.006 * spinDirection;

          // Temporarily boost particle speed in swirl direction
          particle.speedX += Math.cos(swirlAngle) * force * mouseSpeed * 0.003;
          particle.speedY += Math.sin(swirlAngle) * force * mouseSpeed * 0.003;
        }

        // Gradually return rotation speed to original
        particle.rotationSpeed *= 0.96;
        if (Math.abs(particle.rotationSpeed) < 0.001) {
          particle.rotationSpeed = (Math.random() - 0.5) * 0.015;
        }

        // Gradually return particle speed to original (damping)
        particle.speedX *= 0.995;
        particle.speedY *= 0.995;
        // Restore base drift
        if (Math.abs(particle.speedX) < minSpeed) {
          particle.speedX += (Math.random() - 0.5) * 0.01;
        }
        if (Math.abs(particle.speedY) < minSpeed) {
          particle.speedY += (Math.random() - 0.5) * 0.01;
        }

        // Movement
        particle.x += particle.speedX;
        particle.y += particle.speedY;
        particle.rotation += particle.rotationSpeed;

        // Edge wrapping
        if (particle.x < -20) particle.x = width + 20;
        if (particle.x > width + 20) particle.x = -20;
        if (particle.y < -20) particle.y = height + 20;
        if (particle.y > height + 20) particle.y = -20;

        // Calculate opacity with pulsing
        let drawOpacity = particle.opacity;
        if (particle.glowing) {
          const pulse = Math.sin(time * 1.5 + particle.phase) * 0.12 + 0.12;
          drawOpacity = particle.opacity + pulse;
        }

        // Glow effect
        if (particle.glowing) {
          ctx.shadowBlur = 12;
          ctx.shadowColor = `rgba(16, 240, 160, ${drawOpacity * 0.8})`;
        } else {
          ctx.shadowBlur = 0;
        }

        const color = `rgba(16, 240, 160, ${drawOpacity})`;
        drawParticle(ctx, particle, color, time);

        ctx.shadowBlur = 0;
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      clearInterval(spawnInterval);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      if (resizeRafRef.current) {
        cancelAnimationFrame(resizeRafRef.current);
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
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
