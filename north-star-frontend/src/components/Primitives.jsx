import { useEffect, useState } from "react";
import { useCountUp, scoreBand } from "../hooks";

/** The north-star brand mark (inline SVG, themeable, no asset dependency). */
export function StarMark({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="starGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--star)" />
          <stop offset="1" stopColor="var(--star-deep)" />
        </linearGradient>
      </defs>
      <path
        d="M16 3 L18.4 13.6 L29 16 L18.4 18.4 L16 29 L13.6 18.4 L3 16 L13.6 13.6 Z"
        fill="url(#starGrad)"
      />
    </svg>
  );
}

/**
 * Animated circular score.
 * Ring fills via stroke-dashoffset transition; number counts up in sync.
 */
export function CircularScore({
  score,
  size = 210,
  stroke = 16,
  label = "Overall",
  delay = 300,
}) {
  const { color } = scoreBand(score);
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const value = useCountUp(score, 1500, delay);

  // Kick the ring fill on mount (offset from full -> target).
  const [offset, setOffset] = useState(circ);
  useEffect(() => {
    const t = setTimeout(() => setOffset(circ * (1 - score / 100)), delay);
    return () => clearTimeout(t);
  }, [circ, score, delay]);

  return (
    <div className="ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle className="ring-track" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} />
        <circle
          className="ring-value"
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          stroke={color}
          style={{ color }}
          strokeDasharray={circ}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="ring-center">
        <div>
          <div className="ring-num" style={{ fontSize: size * 0.28 }}>
            {value}
          </div>
          <div className="ring-label">{label}</div>
        </div>
      </div>
    </div>
  );
}

/** Compact ring for section cards. */
export function MiniRing({ score, size = 54, stroke = 6 }) {
  const { color } = scoreBand(score);
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const value = useCountUp(score, 1200, 200);
  const [offset, setOffset] = useState(circ);
  useEffect(() => {
    const t = setTimeout(() => setOffset(circ * (1 - score / 100)), 200);
    return () => clearTimeout(t);
  }, [circ, score]);

  return (
    <div className="ring-wrap mini-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle className="ring-track" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} />
        <circle
          className="ring-value"
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          stroke={color}
          style={{ color }}
          strokeDasharray={circ}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="ring-center">
        <span className="numeric" style={{ fontSize: size * 0.32, color: "var(--text-strong)" }}>
          {value}
        </span>
      </div>
    </div>
  );
}

/** Animated labeled progress bar. */
export function ProgressBar({ label, score, delay = 200 }) {
  const { color } = scoreBand(score);
  const value = useCountUp(score, 1300, delay);
  const [w, setW] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setW(score), delay);
    return () => clearTimeout(t);
  }, [score, delay]);

  return (
    <div className="metric">
      <div className="metric-head">
        <span>{label}</span>
        <span className="val">{value}</span>
      </div>
      <div className="bar">
        <div className="bar-fill" style={{ width: `${w}%`, background: color }} />
      </div>
    </div>
  );
}
