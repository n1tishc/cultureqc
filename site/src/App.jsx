import { useCallback, useEffect, useState } from "react";
import DATA from "./data.json";
import { Rail, ForeEdge } from "./components/Rail";
import Hero from "./components/Hero";
import { Integrate, Measure, Outputs, Recall } from "./components/Overview";
import Leaf from "./components/Leaf";
import Upload from "./components/Upload";
import { Ladder, MeasureTable, Provenance } from "./components/AnalysisSections";
import Chain from "./components/Chain";
import Close from "./components/Close";
import { useRailHeight, useReveals } from "./hooks/useReveals";

const VIEWS = ["overview", "analysis"];

function viewFromHash() {
  const h = (location.hash || "").replace(/^#\/?/, "").split("?")[0];
  return VIEWS.includes(h) ? h : null;
}

export default function App() {
  const L = DATA.leaves;
  const [view, setView] = useState(() => viewFromHash() || "overview");
  /* Set by go() and consumed after the panel is in the tree — the target
     section does not exist to scroll to until the new view has rendered. */
  const [jump, setJump] = useState(null);

  const go = useCallback((name, opts = {}) => {
    const next = VIEWS.includes(name) ? name : "overview";
    setView(next);
    setJump(opts.scrollTo || (opts.keepScroll ? null : "top"));
    if (opts.push !== false && location.hash !== "#/" + next)
      history.pushState({ view: next }, "", "#/" + next);
  }, []);

  useEffect(() => {
    const onPop = () => {
      setView(viewFromHash() || "overview");
      setJump("top");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  /* The hash is the address; make it one on first paint too, so a reload or a
     copied link lands where the visitor actually was. */
  useEffect(() => {
    if (!viewFromHash())
      history.replaceState({ view }, "", "#/" + view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!jump) return;
    setJump(null);
    if (jump === "top") {
      window.scrollTo({ top: 0, behavior: "auto" });
      return;
    }
    const t = document.getElementById(jump);
    if (t)
      requestAnimationFrame(() =>
        t.scrollIntoView({ behavior: "auto", block: "start" }),
      );
  }, [jump]);

  useRailHeight();
  useReveals(view);

  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <div className="grain" aria-hidden="true"></div>

      <Rail view={view} onGo={go} leafCount={L.length} />
      <ForeEdge view={view} />

      <main id="main">
        {/* Both panels stay mounted so the plate timelines, the batch and the
            chain keep their state across a tab switch; only one is ever shown. */}
        <div
          role="tabpanel"
          id="view-overview"
          aria-labelledby="tab-overview"
          tabIndex={0}
          hidden={view !== "overview"}
        >
          <Hero leaves={L} onGo={go} />
          <Outputs leaves={L} />
          <Measure onGo={go} />
          <Recall ladder={DATA.ladder} onGo={go} />
          <Integrate />
        </div>

        <div
          role="tabpanel"
          id="view-analysis"
          aria-labelledby="tab-analysis"
          tabIndex={0}
          hidden={view !== "analysis"}
        >
          <Leaf leaves={L} />
          <Upload />
          <MeasureTable leaves={L} />
          <Ladder ladder={DATA.ladder} />
          <Chain leaves={L} />
          <Provenance />
        </div>

        <Close leaves={L} onGo={go} />
      </main>
    </>
  );
}
