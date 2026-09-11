import { useEffect, useState } from "react";
import DATA from "./data.json";
import Upload from "./components/Upload";
import Chain from "./components/Chain";
import {
  Ladder,
  MeasureTable,
  Provenance,
} from "./components/AnalysisSections";
import { Integrate, Measure } from "./components/Overview";
import { Dashboard, Explorer, Icon } from "./components/Workspace";
import { FLAGGED_LEAF } from "./lib/labels";
import Home from "./components/Home";
import "./refinements.css";
import "./instrument.css";
import Instrument from "./components/Instrument";

const NAV = [
  ["home", "Home", "grid"],
  ["demo", "Demo", "scan"],
  ["upload", "Upload your data", "upload"],
];
const DEMO_NAV = [
  ["overview", "Dataset summary", "grid"],
  ["analysis", "Image explorer", "scan"],
  ["benchmarks", "Benchmarks", "chart"],
  ["audit", "Audit trail", "shield"],
];
const INFO = [
  ["provenance", "Models & provenance", "layers"],
  ["integration", "Integration", "code"],
];
const ROUTES = [...NAV, ...DEMO_NAV, ...INFO];
function readRoute() {
  const value = location.hash.replace(/^#\/?/, "").split("?")[0];
  if (value === "analysis") return "demo";
  return ROUTES.some(([id]) => id === value) ? value : "home";
}
export default function App() {
  const [view, setView] = useState(readRoute);
  const [selected, setSelected] = useState(FLAGGED_LEAF);
  const [menu, setMenu] = useState(false);
  // Visited pages stay mounted so uploads and verification survive navigation.
  const [visited, setVisited] = useState(() => new Set([readRoute()]));
  useEffect(() => {
    const sync = () => {
      const next = readRoute();
      setView(next);
      setVisited((old) => new Set([...old, next]));
      setMenu(false);
      window.scrollTo(0, 0);
      requestAnimationFrame(() =>
        document.getElementById("main")?.focus({ preventScroll: true }),
      );
    };
    window.addEventListener("hashchange", sync);
    if (!location.hash) history.replaceState(null, "", "#/home");
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  useEffect(() => {
    const onEscape = (event) => {
      if (event.key === "Escape" && menu) {
        setMenu(false);
        document.querySelector(".menu-button")?.focus();
      }
    };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [menu]);
  const go = (next) => {
    setMenu(false);
    if (view === next) window.scrollTo(0, 0);
    else location.hash = "/" + next;
  };
  const inspect = (index) => {
    setSelected(index);
    go("demo");
  };
  const title = ROUTES.find(([id]) => id === view)[1];
  const navItem = ([id, label, icon]) => (
    <a
      key={id}
      href={"#/" + id}
      className="nav-link"
      aria-current={
        view === id ||
        (id === "demo" && DEMO_NAV.some(([route]) => route === view))
          ? "page"
          : undefined
      }
      onClick={() => setMenu(false)}
    >
      <Icon name={icon} />
      <span>{label}</span>
      {id === "analysis" && (
        <span className="nav-count">{DATA.leaves.length}</span>
      )}
    </a>
  );
  return (
    <div className="app-shell clean-shell">
      <a
        className="skip"
        href="#main"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar" data-open={menu}>
        <a className="brand" href="#/home">
          <span className="brand-symbol">
            <Icon name="cells" />
          </span>
          culture<span>QC</span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">CQ</span>
          <div>
            Cell culture analysis<small>Image-based quality control</small>
          </div>
        </div>
        <nav aria-label="Workspace">
          <p className="nav-label">Workspace</p>
          {NAV.map(navItem)}
        </nav>
        <div className="sidebar-foot">
          <Icon name="layers" />
          <div>
            Research use
            <small>Inspect evidence before acting</small>
          </div>
        </div>
      </aside>
      {menu && (
        <button
          className="menu-scrim"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="app-body">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            aria-label={menu ? "Close navigation" : "Open navigation"}
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Icon name="menu" />
          </button>
          <div className="breadcrumb">
            cultureQC
            <Icon name="chevron" />
            <strong>{title}</strong>
          </div>
          <span className="reference-badge">
            <span />
            {view === "upload"
              ? "Your workspace"
              : view === "home"
                ? "Cell analysis"
                : "Demo data"}
          </span>
          <a className="button primary top-upload" href="#/upload">
            <Icon name="plus" />
            New analysis
          </a>
        </header>
        <main id="main" tabIndex={-1}>
          {!["home", "overview", "analysis", "demo"].includes(view) && (
            <h1 className="sr">{title}</h1>
          )}
          {visited.has("home") && (
            <div hidden={view !== "home"}>
              <Home leaves={DATA.leaves} onInspect={inspect} />
            </div>
          )}
          {["demo", ...DEMO_NAV.map(([id]) => id)].includes(view) && (
            <div className="demo-context">
              <div>
                <strong>Demo workspace</strong>
                <span>
                  Sample images · precomputed results · {DATA.leaves.length}{" "}
                  specimens
                </span>
              </div>
              <nav aria-label="Demo views">
                {[
                  ["demo", "Image explorer"],
                  ["overview", "Dataset summary"],
                  ["benchmarks", "Benchmarks"],
                  ["audit", "Audit trail"],
                ].map(([id, label]) => (
                  <a
                    key={id}
                    href={"#/" + id}
                    aria-current={
                      view === id || (id === "demo" && view === "analysis")
                        ? "page"
                        : undefined
                    }
                  >
                    {label}
                  </a>
                ))}
              </nav>
            </div>
          )}
          {visited.has("demo") && (
            <div hidden={view !== "demo"}>
              <Instrument demo />
              <Explorer
                leaves={DATA.leaves}
                selected={selected}
                onSelect={setSelected}
              />
            </div>
          )}
          {visited.has("overview") && (
            <div hidden={view !== "overview"}>
              <Dashboard leaves={DATA.leaves} onInspect={inspect} onGo={go} />
            </div>
          )}
          {visited.has("upload") && (
            <div hidden={view !== "upload"} className="page supporting">
              <Upload />
            </div>
          )}
          {visited.has("benchmarks") && (
            <div hidden={view !== "benchmarks"} className="page supporting">
              <Measure onGo={go} />
              <MeasureTable leaves={DATA.leaves} />
              <Ladder ladder={DATA.ladder} />
            </div>
          )}
          {visited.has("audit") && (
            <div hidden={view !== "audit"} className="page supporting">
              <Chain leaves={DATA.leaves} />
            </div>
          )}
          {visited.has("provenance") && (
            <div hidden={view !== "provenance"} className="page supporting">
              <Provenance />
            </div>
          )}
          {visited.has("integration") && (
            <div hidden={view !== "integration"} className="page supporting">
              <Integrate />
            </div>
          )}
        </main>
        <footer className="app-footer">
          <span>cultureQC · Image to evidence.</span>
          <a href="#/integration">Integration</a>
          <a href="#/provenance">
            QC trained on synthetic data. View model limitations
            <Icon name="arrow" />
          </a>
        </footer>
      </div>
    </div>
  );
}
