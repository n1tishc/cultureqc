import { useEffect, useRef } from "react";
import { RM } from "../lib/motion";

/* A number that counts up in 15 discrete steps.

   The rAF loop writes textContent through a ref rather than through state: 15
   renders per number, four numbers on screen, is jank for something that is
   purely a readout. `delay` holds it at 0.0 until the plate's sweep has passed,
   which is the beat the original cascade was tuned to. */
export default function Counter({ to, ms = 680, delay = 0, runKey, className }) {
  const ref = useRef(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    if (RM.matches) {
      node.textContent = to.toFixed(1);
      return undefined;
    }
    node.textContent = "0.0";
    let raf = 0;
    const start = setTimeout(() => {
      const steps = 15;
      const t0 = performance.now();
      let last = -1;
      const tick = (now) => {
        const p = Math.min(1, (now - t0) / ms);
        const e = 1 - Math.pow(1 - p, 3);
        const q = Math.round(e * steps) / steps;
        if (q !== last) {
          last = q;
          node.textContent = (to * q).toFixed(1);
        }
        if (p < 1) raf = requestAnimationFrame(tick);
        else node.textContent = to.toFixed(1);
      };
      raf = requestAnimationFrame(tick);
    }, delay);

    return () => {
      clearTimeout(start);
      cancelAnimationFrame(raf);
    };
  }, [to, ms, delay, runKey]);

  return (
    <span className={className} ref={ref}>
      0.0
    </span>
  );
}
