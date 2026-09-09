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
        culture<b>QC</b>
      </a>
      <div className="tabs" role="tablist" aria-label="Views">
        {VIEWS.map((v, i) => (
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
            <span className="tnum">{"0" + (i + 1)}</span>
            {LABEL[v]}
          </button>
        ))}
      </div>
      <p className="railmeta">
        Schema 0.2 &middot; <i id="railleaves">{leafCount} leaves</i>
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

  return (
    <nav className="foreedge" aria-label="Sections on this page">
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
