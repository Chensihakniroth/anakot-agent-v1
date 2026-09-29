import React, {useEffect, useRef} from 'react';
import styles from './styles.module.css';

/**
 * Motion-3D hero graphic: a solid-shaded icosahedron wrapped in a counter-rotating
 * wireframe shell, over a radiating line burst. Everything is projected by hand,
 * no three.js, because the repo pins dependencies tightly and a docs site should not
 * ship a WebGL runtime for one decorative canvas.
 */

const PHI = (1 + Math.sqrt(5)) / 2;

const VERTS: number[][] = [
  [-1, PHI, 0], [1, PHI, 0], [-1, -PHI, 0], [1, -PHI, 0],
  [0, -1, PHI], [0, 1, PHI], [0, -1, -PHI], [0, 1, -PHI],
  [PHI, 0, -1], [PHI, 0, 1], [-PHI, 0, -1], [-PHI, 0, 1],
].map(([x, y, z]) => {
  const len = Math.hypot(x, y, z);
  return [x / len, y / len, z / len];
});

const FACES: number[][] = [
  [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
  [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
  [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
];

const LIGHT = (() => {
  const v = [-0.45, 0.72, 0.52];
  const len = Math.hypot(...v);
  return v.map((n) => n / len);
})();

type Point = {x: number; y: number; z: number};

function rotate(p: Point, ax: number, ay: number, az: number): Point {
  let {x, y, z} = p;
  let cos = Math.cos(ay), sin = Math.sin(ay);
  [x, z] = [x * cos - z * sin, x * sin + z * cos];
  cos = Math.cos(ax); sin = Math.sin(ax);
  [y, z] = [y * cos - z * sin, y * sin + z * cos];
  cos = Math.cos(az); sin = Math.sin(az);
  [x, y] = [x * cos - y * sin, x * sin + y * cos];
  return {x, y, z};
}

function normalOf(a: Point, b: Point, c: Point): Point {
  const u = {x: b.x - a.x, y: b.y - a.y, z: b.z - a.z};
  const v = {x: c.x - a.x, y: c.y - a.y, z: c.z - a.z};
  const n = {
    x: u.y * v.z - u.z * v.y,
    y: u.z * v.x - u.x * v.z,
    z: u.x * v.y - u.y * v.x,
  };
  const len = Math.hypot(n.x, n.y, n.z) || 1;
  return {x: n.x / len, y: n.y / len, z: n.z / len};
}

function edgePath(ctx: CanvasRenderingContext2D, pts: Point[], closed: boolean) {
  ctx.beginPath();
  pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  if (closed) ctx.closePath();
}

function project(p: Point, cx: number, cy: number, scale: number, depth: number): Point {
  const k = scale / (p.z + depth);
  return {x: cx + p.x * k, y: cy + p.y * k, z: p.z};
}

interface MotionHeroProps {
  variant?: 'hero' | 'backdrop';
}

export default function MotionHero({variant = 'hero'}: MotionHeroProps): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', {alpha: true});
    if (!ctx) return;

    // Honour the OS reduced-motion setting: draw one static frame, then stop.
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const root = document.documentElement;
    let isDark = root.getAttribute('data-theme') !== 'light';
    let rgb: number[] = [250, 178, 131];
    const rgba = (a: number) => `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;

    // Re-read on every theme change: the accent differs per theme, and the metal
    // needs lighter shading on a pale page or it reads as a black blob.
    const syncTheme = () => {
      isDark = root.getAttribute('data-theme') !== 'light';
      const accent =
        getComputedStyle(root).getPropertyValue('--ifm-color-primary').trim() || '#fab283';
      rgb = accent.startsWith('#')
        ? [1, 3, 5].map((i) => parseInt(accent.slice(i, i + 2), 16))
        : [250, 178, 131];
      draw(0);
    };
    const themeObserver = new MutationObserver(syncTheme);
    themeObserver.observe(root, {attributes: true, attributeFilter: ['data-theme']});

    // Two ray fields at different rates read as depth rather than a flat starburst.
    const rays = Array.from({length: 96}, (_, i) => ({
      angle: (i / 96) * Math.PI * 2,
      len: 0.72 + ((i * 37) % 11) / 26,
      speed: 0.05 + ((i * 13) % 7) / 90,
      phase: (i % 8) * 0.6,
    }));

    let width = 0;
    let height = 0;
    let raf = 0;
    let running = true;
    const pointer = {x: 0, y: 0, tx: 0, ty: 0};

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      // Cap DPR at 2: a 3x phone screen triples the fill cost for no visible gain.
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (t: number) => {
      const time = reduced ? 6 : t / (variant === 'backdrop' ? 2500 : 1000);
      const cx = width / 2 + pointer.x * 26;
      const cy = height / 2 + pointer.y * 20;
      const unit = Math.min(width, height);
      const scale = unit * (variant === 'backdrop' ? 0.72 : 0.42);

      pointer.x += (pointer.tx - pointer.x) * 0.06;
      pointer.y += (pointer.ty - pointer.y) * 0.06;

      ctx.clearRect(0, 0, width, height);

      // Radiating burst behind the solid.
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(time * 0.04);
      ctx.lineWidth = 1;
      for (const ray of rays) {
        const reach = unit * 0.52 * ray.len * (1 + 0.06 * Math.sin(time * ray.speed * 6 + ray.phase));
        const cos = Math.cos(ray.angle);
        const sin = Math.sin(ray.angle);
        // Fade each ray out with distance so the burst dissolves instead of ending flat.
        const grad = ctx.createLinearGradient(cos * unit * 0.12, sin * unit * 0.12, cos * reach, sin * reach);
        grad.addColorStop(0, rgba(isDark ? 0.5 : 0.4));
        grad.addColorStop(1, rgba(0));
        ctx.strokeStyle = grad;
        ctx.beginPath();
        ctx.moveTo(cos * unit * 0.12, sin * unit * 0.12);
        ctx.lineTo(cos * reach, sin * reach);
        ctx.stroke();
      }
      ctx.restore();

      const spin = (p: Point, ax: number, ay: number, az: number) => rotate(p, ax, ay, az);

      // Outer wireframe shell: counter-rotates for parallax against the solid.
      const wire: Point[] = VERTS.map((v) =>
        project(spin({x: v[0], y: v[1], z: v[2]}, time * 0.34, time * -0.48, 0.18), cx, cy, scale * 1.42, 3.2)
      );
      ctx.lineWidth = 1;
      for (const face of FACES) {
        const pts = face.map((i) => wire[i]);
        const facing = (pts[0].z + pts[1].z + pts[2].z) / 3;
        const depth = (facing + 3.2) / 6.4;
        ctx.strokeStyle = rgba((isDark ? 0.1 : 0.14) + depth * (isDark ? 0.3 : 0.34));
        edgePath(ctx, pts, true);
        ctx.stroke();
      }

      // The background keeps only the shell and rays; solid facets compete with copy.
      if (variant === 'backdrop') return;

      // Inner solid: Lambert-shaded facets for the chrome read.
      const solid: Point[] = VERTS.map((v) =>
        project(spin({x: v[0], y: v[1], z: v[2]}, time * 0.46, time * 0.62, 0), cx, cy, scale, 3)
      );
      for (const face of FACES) {
        const [a, b, c] = face.map((i) => solid[i]);
        const n = normalOf(
          rotate({x: VERTS[face[0]][0], y: VERTS[face[0]][1], z: VERTS[face[0]][2]}, time * 0.46, time * 0.62, 0),
          rotate({x: VERTS[face[1]][0], y: VERTS[face[1]][1], z: VERTS[face[1]][2]}, time * 0.46, time * 0.62, 0),
          rotate({x: VERTS[face[2]][0], y: VERTS[face[2]][1], z: VERTS[face[2]][2]}, time * 0.46, time * 0.62, 0)
        );
        const facing = n.z < 0;
        if (!facing) continue;
        const lambert = Math.max(0, n.x * LIGHT[0] + n.y * LIGHT[1] + n.z * LIGHT[2]);
        // Ambient floor keeps unlit facets readable instead of collapsing to a black blob.
        const shade = 0.30 + lambert * 0.70;
        // Two-lobe specular: a broad sheen plus a tight hot-spot reads as polished metal.
        const spec = Math.pow(lambert, 6) * 0.28 + Math.pow(lambert, 40) * 0.85;
        // A fixed near-black body disappears on a light page, so the base tone
        // and its lift both follow the theme.
        const base = isDark ? 30 : 52;
        const lift = isDark ? 168 : 150;
        ctx.fillStyle = `rgba(${Math.round(base + shade * lift)},${Math.round((isDark ? 27 : 46) + shade * (isDark ? 160 : 142))},${Math.round((isDark ? 33 : 52) + shade * (isDark ? 150 : 132))},${0.95})`;
        edgePath(ctx, [a, b, c], true);
        ctx.fill();
        if (spec > 0.02) {
          ctx.fillStyle = `rgba(255,246,235,${spec})`;
          ctx.fill();
        }
        const rim = Math.pow(1 - lambert, 3) * 0.5;
        ctx.strokeStyle = rgba((isDark ? 0.14 : 0.2) + rim);
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }

      // A slowly counter-spinning inner core adds a third depth layer.
      const core: Point[] = VERTS.map((v) =>
        project(spin({x: v[0], y: v[1], z: v[2]}, -time * 0.5, -time * 0.7, 0), cx, cy, scale * 0.5, 2.6)
      );
      ctx.lineWidth = 0.8;
      for (const face of FACES) {
        const pts = face.map((i) => core[i]);
        const depth = ((pts[0].z + pts[1].z + pts[2].z) / 3 + 2.6) / 5.2;
        ctx.strokeStyle = rgba((isDark ? 0.22 : 0.26) + depth * (isDark ? 0.5 : 0.44));
        edgePath(ctx, pts, true);
        ctx.stroke();
      }
    };

    // Safe to call now that draw is initialised.
    syncTheme();

    const loop = (t: number) => {
      if (running) draw(t);
      raf = requestAnimationFrame(loop);
    };

    resize();
    const onResize = () => {
      resize();
      if (reduced) draw(0);
    };
    window.addEventListener('resize', onResize);

    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.tx = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      pointer.ty = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };
    const onLeave = () => {
      pointer.tx = 0;
      pointer.ty = 0;
    };
    if (!reduced) {
      canvas.addEventListener('pointermove', onMove);
      canvas.addEventListener('pointerleave', onLeave);
    }

    // Stop burning CPU when the tab is hidden or the hero scrolls out of view.
    const onVisibility = () => {
      running = !document.hidden;
    };
    document.addEventListener('visibilitychange', onVisibility);

    let observer: IntersectionObserver | undefined;
    if (!reduced && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(
        ([entry]) => {
          running = !document.hidden && entry.isIntersecting;
        },
        {threshold: 0}
      );
      observer.observe(canvas);
    }

    if (reduced) {
      draw(0);
    } else {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      document.removeEventListener('visibilitychange', onVisibility);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerleave', onLeave);
      observer?.disconnect();
      themeObserver.disconnect();
    };
  }, [variant]);

  return (
    <div className={styles.stage} aria-hidden="true">
      <canvas ref={canvasRef} className={styles.canvas} />
    </div>
  );
}
