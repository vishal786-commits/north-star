import { useEffect, useRef, useState } from "react";

const prefersReduced = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Animate a number from 0 -> target once, on mount.
 * Returns the current value to render.
 */
export function useCountUp(target, duration = 1500, delay = 200) {
  const [value, setValue] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    if (prefersReduced()) {
      setValue(target);
      return;
    }
    let start = null;
    const startTimeout = setTimeout(() => {
      const tick = (ts) => {
        if (start === null) start = ts;
        const p = Math.min((ts - start) / duration, 1);
        // easeOutCubic
        const eased = 1 - Math.pow(1 - p, 3);
        setValue(Math.round(target * eased));
        if (p < 1) raf.current = requestAnimationFrame(tick);
      };
      raf.current = requestAnimationFrame(tick);
    }, delay);

    return () => {
      clearTimeout(startTimeout);
      cancelAnimationFrame(raf.current);
    };
  }, [target, duration, delay]);

  return value;
}

/** Map a 0–100 score to a semantic band + its CSS color variable. */
export function scoreBand(score) {
  if (score >= 80) return { band: "high", color: "var(--band-high)" };
  if (score >= 55) return { band: "mid", color: "var(--band-mid)" };
  return { band: "low", color: "var(--band-low)" };
}
