"use client";

import styles from "./lotus-bloom.module.css";

// The 5 petals of public/logo.svg. Each begins rotated to vertical (standing, stacked over the
// centre petal) and falls outward to its natural place. `startAngle` is the NEGATIVE of the
// petal's fanned angle about the base point (≈ centre 0°, side ±35°, outer ±71°), so at the start
// every petal points straight up; animating rotate(startAngle) → rotate(0) lets them fall open
// left & right. The outer pair lags slightly so the lotus cascades open.
const PETALS: { d: string; startAngle: number; delayMs: number }[] = [
  // centre (already vertical — stays put as the standing reference)
  { d: "M43.7381 55.5287C37.3035 50.9615 27.141 37.9122 43.7381 23.2317C60.3374 37.9122 50.1754 50.9615 43.7381 55.5287Z", startAngle: 0, delayMs: 0 },
  // upper-right → falls right
  { d: "M44.5719 55.616C52.3993 55.4276 68.1612 50.2666 63.4076 28.7158C58.4738 29.371 54.6804 30.7217 51.7925 32.5059", startAngle: -35, delayMs: 0 },
  // upper-left → falls left
  { d: "M43.5025 55.616C35.6751 55.4277 19.9132 50.2667 24.6668 28.7159C29.7436 29.3901 33.6129 30.8006 36.5307 32.6622", startAngle: 35, delayMs: 0 },
  // lower-left outer → falls further left (lags)
  { d: "M43.5397 56.406C37.0199 60.7413 21.1482 65.5543 12.6811 45.1744C17.0477 42.9076 20.8912 41.8365 24.2525 41.624", startAngle: 71, delayMs: 120 },
  // lower-right outer → falls further right (lags)
  { d: "M44.5306 56.4056C51.0504 60.7409 66.9221 65.554 75.3892 45.174C70.9855 42.8879 67.1138 41.8181 63.7323 41.6184", startAngle: -71, delayMs: 120 },
];

export type LotusBloomProps = {
  /** Rendered size in px (square). */
  size?: number;
  /** Per-petal fall duration in ms ("not too quick, not too slow"). */
  durationMs?: number;
  /** Loop forever (open ⇄ close) — used as the "generating" indicator. Default plays once. */
  loop?: boolean;
  /** Change this value to replay the animation (remounts the SVG). */
  replayKey?: number | string;
  className?: string;
  style?: React.CSSProperties;
};

/**
 * Animated Astro Agent lotus: the 5 petals start overlapped at the base point and bloom outward.
 * Uses animate.css for the container fade; a custom keyframe (lotus-bloom.module.css) does the
 * shared-base-point fan that animate.css presets can't express.
 */
export function LotusBloom({ size = 220, durationMs = 1100, loop = false, replayKey = 0, className, style }: LotusBloomProps) {
  const petalClass = `${styles.petal}${loop ? ` ${styles.loop}` : ""}`;
  return (
    <div
      key={replayKey}
      className={`animate__animated animate__fadeIn ${className ?? ""}`}
      style={{ "--animate-duration": "500ms", color: "var(--primary)", ...style } as React.CSSProperties}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 88 88"
        fill="none"
        role="img"
        aria-label="Astro Agent lotus blooming"
        xmlns="http://www.w3.org/2000/svg"
      >
        {PETALS.map((p, i) => (
          <path
            key={i}
            d={p.d}
            className={petalClass}
            stroke="currentColor"
            strokeWidth={4.125}
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              animationDelay: `${p.delayMs}ms`,
              "--start-angle": `${p.startAngle}deg`,
              "--fall-duration": `${durationMs}ms`,
            } as React.CSSProperties}
          />
        ))}
      </svg>
    </div>
  );
}
