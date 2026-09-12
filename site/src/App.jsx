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
import NotFound from "./components/NotFound";
import EngineeringNotes from "./components/EngineeringNotes";
import useUploadWorkspace from "./hooks/useUploadWorkspace";
import { CONTACT, LINKEDIN_URL, REPO_URL } from "./config";
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
  ["notes", "Engineering notes", "code"],
];
const ROUTES = [...NAV, ...DEMO_NAV, ...INFO];

/* Per-route <title>/description, restored on the way back to Home (F4, F14). */
const HOME_TITLE =
  "cultureQC — brightfield image analysis for automated cell culture";
const HOME_DESCRIPTION =
  "cultureQC reads one phase-contrast image and returns a confluency estimate, a QC flag with visual evidence, a recommended action, and a hash-chained record built for GMP traceability. Vendor-neutral software, not an instrument.";
const TITLE_META = {
  home: { label: "Home", title: HOME_TITLE, description: HOME_DESCRIPTION },
  demo: {
    label: "Image explorer",
    title: "Image explorer · cultureQC",
    description:
      "Browse recorded specimens, toggle segmentation overlays, and inspect confluency and QC results.",
  },
  overview: {
    label: "Dataset summary",
    title: "Dataset summary · cultureQC",
    description:
      "Summary of the sample images in the demo dataset and their recorded analysis results.",
  },
  benchmarks: {
    label: "Benchmarks",
    title: "Benchmarks · cultureQC",
    description:
      "Confluency and contamination-recall benchmarks, and the honest limits behind them.",
  },
  audit: {
    label: "Audit trail",
    title: "Audit trail · cultureQC",
    description:
      "Recompute and verify the SHA-256 hash chain behind every analysed record, in your browser.",
  },
  upload: {
    label: "Upload your data",
    title: "Upload your data · cultureQC",
    description:
      "Analyse your own microscopy images and review confluency and quality flags.",
  },
  integration: {
    label: "Integration",
    title: "Integration · cultureQC",
    description:
      "Vendor-neutral integration: API shape, record schema, and a code sample.",
  },
  provenance: {
    label: "Models & provenance",
    title: "Models & provenance · cultureQC",
    description:
      "Model versions, training-data limitations, and the record schema behind every result.",
  },
  notes: {
    label: "Engineering notes",
    title: "Engineering notes · cultureQC",
    description:
      "Test suite, CI, training data, and the record schema behind cultureQC.",
  },
  notfound: {
    label: "Not found",
    title: "Page not found · cultureQC",
    description: "This page does not exist.",
  },
};
const NO_GENERIC_H1 = ["home", "overview", "analysis", "demo", "notfound", "notes"];

function readRoute() {
  const value = location.hash.replace(/^#\/?/, "").split("?")[0];
  if (value === "analysis") return "demo";
  if (value === "") return "home";
  return ROUTES.some(([id]) => id === value) ? value : "notfound";
}
export default function App() {
  const [view, setView] = useState(readRoute);
  const [selected, setSelected] = useState(FLAGGED_LEAF);
  const [menu, setMenu] = useState(false);
  /* Upload/analysis state lives here, one level above every route, so the
     Upload route can safely unmount on navigation (F2) without losing an
     in-progress batch, and so the Audit route can fold analysed uploads into
     the chain it displays (F8). */
  const workspace = useUploadWorkspace();
  useEffect(() => {
    const sync = () => {
      setView(readRoute());
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
  /* Per-route title, meta description, and OG tags (F4, F14). Home restores
     the site's default descriptive title rather than leaving a stale one. */
  useEffect(() => {
    const meta = TITLE_META[view] || TITLE_META.home;
    document.title = meta.title;
    const setContent = (selector, value) => {
      document.querySelector(selector)?.setAttribute("content", value);
    };
    setContent('meta[name="description"]', meta.description);
    setContent('meta[property="og:title"]', meta.title);
    setContent('meta[property="og:description"]', meta.description);
  }, [view]);
  const go = (next) => {
    setMenu(false);
    if (view === next) window.scrollTo(0, 0);
    else location.hash = "/" + next;
  };
  const inspect = (index) => {
    setSelected(index);
    go("demo");
  };
  const title = (TITLE_META[view] || TITLE_META.home).label;
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
                : view === "notes" || view === "notfound"
                  ? "cultureQC"
                  : "Demo data"}
          </span>
          {workspace.analysing && view !== "upload" && (
            <a
              className="analysing-pill"
              href="#/upload"
              role="status"
              aria-live="polite"
            >
              <i aria-hidden="true" />
              {workspace.prog.text}
            </a>
          )}
          <a className="button primary top-upload" href="#/upload">
            <Icon name="plus" />
            New analysis
          </a>
        </header>
        <main id="main" tabIndex={-1}>
          {!NO_GENERIC_H1.includes(view) && (
            <h1 className="sr">{title}</h1>
          )}
          {view === "home" && <Home leaves={DATA.leaves} onInspect={inspect} />}
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
          {view === "demo" && (
            <>
              <Instrument demo />
              <Explorer
                leaves={DATA.leaves}
                selected={selected}
                onSelect={setSelected}
              />
            </>
          )}
          {view === "overview" && (
            <Dashboard leaves={DATA.leaves} onInspect={inspect} onGo={go} />
          )}
          {view === "upload" && (
            <div className="page supporting">
              <Upload workspace={workspace} />
            </div>
          )}
          {view === "benchmarks" && (
            <div className="page supporting">
              <Measure onGo={go} />
              <MeasureTable leaves={DATA.leaves} />
              <Ladder ladder={DATA.ladder} />
            </div>
          )}
          {view === "audit" && (
            <div className="page supporting">
              <Chain leaves={DATA.leaves} sessionFiles={workspace.files} />
            </div>
          )}
          {view === "provenance" && (
            <div className="page supporting">
              <Provenance />
            </div>
          )}
          {view === "integration" && (
            <div className="page supporting">
              <Integrate />
            </div>
          )}
          {view === "notes" && (
            <div className="page supporting">
              <EngineeringNotes />
            </div>
          )}
          {view === "notfound" && <NotFound />}
        </main>
        <footer className="app-footer">
          <span>cultureQC · Image to evidence.</span>
          <a href="#/notes">Engineering notes</a>
          <a href="#/integration">Integration</a>
          {REPO_URL ? (
            <a href={REPO_URL} target="_blank" rel="noopener">
              Source
            </a>
          ) : (
            <span className="footer-pending">Source &mdash; pending</span>
          )}
          {LINKEDIN_URL && (
            <a href={LINKEDIN_URL} target="_blank" rel="noopener">
              LinkedIn
            </a>
          )}
          {CONTACT && <a href={"mailto:" + CONTACT}>Contact</a>}
          <a href="#/provenance">
            QC trained on synthetic data. View model limitations
            <Icon name="arrow" />
          </a>
        </footer>
      </div>
    </div>
  );
}
