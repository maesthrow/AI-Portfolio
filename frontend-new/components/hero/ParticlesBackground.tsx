"use client";

import { useEffect, useRef } from "react";

type ParticleShape =
  | "bracket"
  | "hash"
  | "slash"
  | "pipe"
  | "binary"
  | "asterisk"
  | "chevron"
  | "dot";

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
  charValue: string;
}

const SHAPES: ParticleShape[] = [
  "bracket", "hash", "slash", "pipe", "binary",
  "asterisk", "chevron", "dot"
];

const BRACKET_CHARS = ["{}", "[]", "()", "<>", "/*", "*/", "//"];
const BINARY_CHARS = ["0", "1", "00", "01", "010", "011"];
const CHEVRON_CHARS = ["<", ">", "<<", ">>", "</", "/>"];

function getCharForShape(shape: ParticleShape): string {
  switch (shape) {
    case "bracket":
      return BRACKET_CHARS[Math.floor(Math.random() * BRACKET_CHARS.length)];
    case "hash":
      return "#";
    case "slash":
      return Math.random() > 0.5 ? "/" : "\\";
    case "pipe":
      return Math.random() > 0.5 ? "|" : "||";
    case "binary":
      return BINARY_CHARS[Math.floor(Math.random() * BINARY_CHARS.length)];
    case "asterisk":
      return Math.random() > 0.5 ? "*" : "**";
    case "chevron":
      return CHEVRON_CHARS[Math.floor(Math.random() * CHEVRON_CHARS.length)];
    case "dot":
      return Math.random() > 0.7 ? "..." : "::";
    default:
      return "#";
  }
}

function createParticle(width: number, height: number): Particle {
  const shapeIndex = Math.floor(Math.random() * SHAPES.length);
  const shape = SHAPES[shapeIndex];
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 5 + 3,
    speedX: (Math.random() - 0.5) * 0.4,
    speedY: (Math.random() - 0.5) * 0.4,
    opacity: Math.random() * 0.25 + 0.08,
    glowing: Math.random() > 0.75,
    phase: Math.random() * Math.PI * 2,
    shape,
    rotation: (Math.random() - 0.5) * 0.3,
    rotationSpeed: (Math.random() - 0.5) * 0.008,
    charValue: getCharForShape(shape)
  };
}

function drawParticle(
  ctx: CanvasRenderingContext2D,
  particle: Particle,
  color: string
) {
  ctx.save();
  ctx.translate(particle.x, particle.y);
  ctx.rotate(particle.rotation);

  const fontSize = Math.max(10, particle.size * 2.2);
  ctx.fillStyle = color;
  ctx.font = `${fontSize}px "Space Grotesk", monospace`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(particle.charValue, 0, 0);

  ctx.restore();
}

export function ParticlesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>(0);
  const mousePosRef = useRef({ x: -1000, y: -1000 });
  const prevMousePosRef = useRef({ x: -1000, y: -1000 });
  const mouseVelocityRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

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

    const particleCount = Math.min(80, Math.max(35, Math.floor(width / 20)));
    particlesRef.current = Array.from({ length: particleCount }, () =>
      createParticle(width, height)
    );

    const handleResize = () => {
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

      prevMousePosRef.current = prev;
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

      particlesRef.current.forEach((particle) => {
        // Distance from mouse
        const dx = particle.x - mousePos.x;
        const dy = particle.y - mousePos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < effectRadius && distance > 0) {
          const force = ((effectRadius - distance) / effectRadius) * 0.8;

          // Direction from mouse to particle
          const pushAngle = Math.atan2(dy, dx);

          // Combine radial push with velocity-based push
          const pushX = Math.cos(pushAngle) * force * 2.5 + mouseVel.x * force * 0.12;
          const pushY = Math.sin(pushAngle) * force * 2.5 + mouseVel.y * force * 0.12;

          particle.x += pushX;
          particle.y += pushY;

          // Add spin based on mouse movement (vortex effect)
          particle.rotationSpeed += force * mouseSpeed * 0.003 * (Math.random() > 0.5 ? 1 : -1);
        }

        // Gradually return rotation speed to original
        particle.rotationSpeed *= 0.98;
        if (Math.abs(particle.rotationSpeed) < 0.001) {
          particle.rotationSpeed = (Math.random() - 0.5) * 0.02;
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
        drawParticle(ctx, particle, color);

        ctx.shadowBlur = 0;
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
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
