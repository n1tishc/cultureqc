import { useEffect } from "react";

/* Scroll reveal, re-armed whenever the view changes.

   The observer alone is not enough: an element observed while its panel was
   hidden, or one jumped past by a fast scroll, can stay at opacity 0 while
   sitting in full view. Reveal is decoration — never a reason for a visitor to
   face empty ground — so pokeReveals promotes anything on screen
   unconditionally, on every scroll and resize. */
export function useReveals(view) {
  useEffect(() => {
    const io = new IntersectionObserver(
      (es, o) => {
        es.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            o.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
    );

    const observe = () =>
      document.querySelectorAll(".rv:not(.in)").forEach((n) => io.observe(n));

    const poke = (edge) => {
      const H = window.innerHeight;
      const limit = edge === "full" ? H : H * 0.94;
      document.querySelectorAll(".rv:not(.in)").forEach((n) => {
        const r = n.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return; /* still in a hidden panel */
        if (r.top < limit && r.bottom > 0) n.classList.add("in");
      });
    };

    /* The freshly shown panel's elements had zero rects until now: observe after
       a frame so they get a real initial callback, then promote what is in view. */
    observe();
    const raf = requestAnimationFrame(() => poke());

    /* Fires once scrolling settles, never during it, so the observer keeps
       owning the staggered entrance and this only sweeps up what it missed. */
    let timer = 0;
    const queue = () => {
      clearTimeout(timer);
      timer = setTimeout(() => poke("full"), 220);
    };
    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", queue);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
      window.removeEventListener("scroll", queue);
      window.removeEventListener("resize", queue);
      io.disconnect();
    };
  }, [view]);
}

/* Publish the rail's real height so scroll-margin-top can clear it. It wraps at
   narrow widths, so this is measured rather than guessed, and re-measured on
   resize and after the fonts land (which changes the wrap point). Without it,
   an anchored heading lands underneath the sticky rail on a phone. */
export function useRailHeight() {
  useEffect(() => {
    const measure = () => {
      const r = document.querySelector(".rail");
      if (r)
        document.documentElement.style.setProperty(
          "--rail-h",
          r.offsetHeight + "px",
        );
    };
    measure();
    window.addEventListener("resize", measure);
    if (document.fonts && document.fonts.ready)
      document.fonts.ready.then(measure);
    return () => window.removeEventListener("resize", measure);
  }, []);
}
