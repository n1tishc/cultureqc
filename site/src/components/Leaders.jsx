import { useCallback, useEffect, useRef, useState } from "react";

/* Leader lines.

   Every printed reading is ruled back to the pixels that produced it, the way a
   plate pins its annotations to nodes rather than leaving them to sit near each
   other and hope. The geometry is measured off the live layout — there is no
   fixed grid to trust, because the plate fits itself to its container and the
   readouts wrap with the type.

   Purely decorative to assistive technology: both ends are already named in
   words, so a screen reader gains nothing from the rule between them. */

/* Below this width the columns stack and a rule between them would cross the
   whole page rather than connect two things that sit side by side. */
const MIN_WIDTH = 1080;

export default function Leaders({ hostRef, pairs, redrawKey }) {
  const [segments, setSegments] = useState([]);
  const [box, setBox] = useState(null);
  const raf = useRef(0);

  const measure = useCallback(() => {
    const host = hostRef.current;
    if (!host) return;
    if (window.innerWidth < MIN_WIDTH) {
      setSegments([]);
      return;
    }
    const h = host.getBoundingClientRect();
    setBox({ w: h.width, h: h.height });

    const next = [];
    pairs.forEach(({ from, to }, i) => {
      const a = document.querySelector(from);
      const b = document.querySelector(to);
      if (!a || !b) return;
      const ra = a.getBoundingClientRect();
      const rb = b.getBoundingClientRect();
      if (!ra.width || !rb.width) return;

      /* Leave from whichever side of the reading faces its evidence, and arrive
         on the facing edge of the evidence. Which side that is depends on the
         layout, not on an assumption: the readings sit right of the plate in
         the analysis instrument and left of it in the first viewport. */
      const leftToRight = ra.right <= rb.left;
      const x1 = (leftToRight ? ra.right + 8 : ra.left - 8) - h.left;
      const y1 = ra.top - h.top + ra.height / 2;
      const x2 = (leftToRight ? rb.left - 6 : rb.right + 6) - h.left;
      const y2 = rb.top - h.top + rb.height / 2;

      /* Overlapping horizontally means there is no gap to rule across, and a
         line drawn anyway would cross the very thing it points at. */
      const gap = Math.abs(x2 - x1);
      if ((leftToRight && x2 <= x1) || (!leftToRight && x2 >= x1)) return;
      if (gap < 24) return;

      /* A document's leader: a short shoulder off the reading, one diagonal
         run, then a shoulder into the target. */
      const dir = leftToRight ? 1 : -1;
      const shoulder = Math.min(26, gap / 3) * dir;
      const d = `M${x1} ${y1} H${x1 + shoulder} L${x2 - shoulder} ${y2} H${x2}`;
      next.push({ d, x1, y1, x2, y2, key: from + i });
    });
    setSegments(next);
  }, [hostRef, pairs]);

  const schedule = useCallback(() => {
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(measure);
  }, [measure]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;

    schedule();

    const ro = new ResizeObserver(schedule);
    ro.observe(host);

    /* The evidence boxes are added and removed by the plate's own timeline, and
       the readouts change text as the counter lands. Watch for both rather than
       measuring once and drifting. */
    const mo = new MutationObserver(schedule);
    mo.observe(host, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["data-boxes", "data-mask", "data-v", "style"],
    });

    window.addEventListener("resize", schedule);
    window.addEventListener("scroll", schedule, { passive: true });
    if (document.fonts && document.fonts.ready)
      document.fonts.ready.then(schedule);

    return () => {
      cancelAnimationFrame(raf.current);
      ro.disconnect();
      mo.disconnect();
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule);
    };
  }, [hostRef, schedule, redrawKey]);

  if (!box || segments.length === 0) return null;

  return (
    <svg
      className="leaders"
      aria-hidden="true"
      focusable="false"
      viewBox={`0 0 ${box.w} ${box.h}`}
      width={box.w}
      height={box.h}
    >
      {segments.map((s) => (
        <g key={s.key}>
          <path d={s.d} />
          <circle cx={s.x1} cy={s.y1} r="2.4" />
          <circle cx={s.x2} cy={s.y2} r="2.4" />
        </g>
      ))}
    </svg>
  );
}
