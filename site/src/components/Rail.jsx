import { useEffect, useRef, useState } from "react";
import { RM } from "../lib/motion";

const VIEWS = ["overview", "analysis"];
const LABEL = { overview: "Overview", analysis: "Analysis" };

export function Rail({ view, onGo, leafCount }) {
  const refs = useRef({});

  const onKeyDown = (e) => {
    const i = VIEWS.indexOf(view);
    let j = -1;
    if (e.key === "ArrowRight") j = (i + 1) % VIEWS.length;
    else if (e.key === "ArrowLeft") j = (i - 1 + VIEWS.length) % VIEWS.length;
    else if (e.key === "Home") j = 0;
    else if (e.key === "End") j = VIEWS.length - 1;
    if (j >= 0) {
      e.preventDefault();
      onGo(VIEWS[j]);
      /* Roving tabindex: the newly selected tab has to take focus, or a keyboard
         user is left on a control that is now tabindex -1. */
      requestAnimationFrame(() => {
        const n = refs.current[VIEWS[j]];
        if (n) n.focus();
      });
    }
  };

  return (
    <header className="rail">
      <a
        className="mark"
        href="#/overview"
        onClick={(e) => {
          e.preventDefault();
          onGo("overview");
        }}
      >
        {/* The logomark. Authored, one stroke weight: a dish of cells, ruled
            like the field the pipeline measures. */}
        <svg className="logomark" viewBox="0 0 96 96" aria-hidden="true">
          <g fill="none" stroke="currentColor" strokeWidth="2.4">
            <circle cx="48" cy="48" r="43" />
            <circle cx="48" cy="48" r="25" strokeWidth="1.4" />
          </g>
          <g fill="currentColor">
            <ellipse cx="39" cy="37" rx="5.2" ry="2.5" transform="rotate(-28 39 37)" />
            <ellipse cx="52" cy="34" rx="4.1" ry="2.2" transform="rotate(64 52 34)" />
            <ellipse cx="61" cy="44" rx="5.6" ry="2.4" transform="rotate(-12 61 44)" />
            <ellipse cx="36" cy="52" rx="4.4" ry="2.3" transform="rotate(18 36 52)" />
            <ellipse cx="49" cy="59" rx="5.8" ry="2.6" transform="rotate(-46 49 59)" />
            <ellipse cx="60" cy="60" rx="3.9" ry="2.1" transform="rotate(30 60 60)" />
            <ellipse cx="47" cy="46" rx="3.2" ry="1.9" transform="rotate(78 47 46)" />
          </g>
        </svg>
        culture<b>QC</b>
      </a>
      <div className="tabs" role="tablist" aria-label="Views">
        {VIEWS.map((v) => (
          <button
            className="tab"
            key={v}
            role="tab"
            id={"tab-" + v}
            type="button"
            ref={(n) => (refs.current[v] = n)}
            aria-controls={"view-" + v}
            aria-selected={String(view === v)}
            tabIndex={view === v ? 0 : -1}
            onClick={() => onGo(v)}
            onKeyDown={onKeyDown}
          >
            {/* No 01 / 02 here: numbering two items carries nothing. The
                booklet's real numbering — 9 leaves, Leaf 05 / 09 — is where a
                figure actually tells the reader something. */}
            {LABEL[v]}
          </button>
        ))}
      </div>
      <p className="railmeta">
        Schema 0.2
        <i id="railleaves">{leafCount} records</i>
      </p>
    </header>
  );
}

const SECTIONS = {
  overview: [
    ["sec-hero", "Top"],
    ["sec-outputs", "Outputs"],
    ["sec-measure", "Confluency"],
    ["sec-recall", "Recall"],
    ["sec-integrate", "Integration"],
    ["sec-close", "Close"],
  ],
  analysis: [
    ["sec-leaf", "Specimens"],
    ["sec-upload", "Your files"],
    ["sec-measure2", "Confluency"],
    ["sec-ladder", "Matrix"],
    ["sec-chain", "Audit"],
    ["sec-provenance", "Provenance"],
    ["sec-close", "Close"],
  ],
};

/* The fore-edge index: the page's own section list, marking where you are.
   Placed after the primary nav in the DOM so the tab bar is not buried behind
   seven section jumps for a keyboard or screen-reader user. */
export function ForeEdge({ view }) {
  const navRef = useRef(null);
  const list = SECTIONS[view];
  const [here, setHere] = useState(list[0][0]);

  useEffect(() => {
    setHere(list[0][0]);
    const io = new IntersectionObserver(
      (es) => {
        es.forEach((e) => {
          if (e.isIntersecting) setHere(e.target.id);
        });
      },
      { rootMargin: "-45% 0px -50% 0px" },
    );
    list.forEach(([id]) => {
      const n = document.getElementById(id);
      if (n) io.observe(n);
    });
    return () => io.disconnect();
  }, [view, list]);

  // Keep the current section discoverable in the narrow-screen index without
  // moving the page or stealing keyboard focus.
  useEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector('[aria-current="true"]');
    if (!active) return;
    const left = active.offsetLeft - nav.offsetLeft;
    if (left < nav.scrollLeft)
      nav.scrollLeft = left;
    else if (left + active.offsetWidth > nav.scrollLeft + nav.clientWidth)
      nav.scrollLeft = left + active.offsetWidth - nav.clientWidth;
  }, [here]);

  return (
    <nav ref={navRef} className="foreedge" aria-label="Sections on this page">
      {list.map(([id, name]) => (
        <button
          className="fe-link"
          key={id}
          type="button"
          data-target={id}
          aria-current={String(here === id)}
          onClick={() => {
            const t = document.getElementById(id);
            if (t)
              t.scrollIntoView({
                behavior: RM.matches ? "auto" : "smooth",
                block: "start",
              });
          }}
        >
          <span>{name}</span>
        </button>
      ))}
    </nav>
  );
}
