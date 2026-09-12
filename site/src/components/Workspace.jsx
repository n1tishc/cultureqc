import { useState } from "react";
import Plate from "./Plate";
import {
  ACTION_LABEL,
  ACTION_TONE,
  CLASSES,
  FLAG_LABEL,
  FLAG_SHORT,
  FLAG_TONE,
  FLAGGED_LEAF,
} from "../lib/labels";

const PATHS = {
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  scan: (
    <>
      <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />
      <circle cx="12" cy="12" r="4" />
    </>
  ),
  upload: (
    <path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5" />
  ),
  chart: <path d="M4 3v17h17M9 16v-5m5 5V6m5 10V9" />,
  shield: (
    <>
      <path d="m12 3 8 3v6c0 4-3 7-8 9-5-2-8-5-8-9V6l8-3Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
  layers: <path d="m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5" />,
  code: <path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18" />,
  cells: (
    <>
      <circle cx="12" cy="12" r="9" />
      <ellipse cx="9" cy="8" rx="2" ry="1" transform="rotate(-30 9 8)" />
      <ellipse cx="16" cy="11" rx="1" ry="2" />
      <ellipse cx="10" cy="16" rx="2.5" ry="1" transform="rotate(25 10 16)" />
    </>
  ),
  arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  plus: <path d="M12 4v16M4 12h16" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  search: (
    <>
      <circle cx="10" cy="10" r="6" />
      <path d="m15 15 6 6" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  alert: <path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v.2" />,
  download: <path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4" />,
  copy: (
    <>
      <rect x="8" y="8" width="12" height="13" rx="2" />
      <path d="M16 8V3H3v13h5" />
    </>
  ),
};
export function Icon({ name, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {PATHS[name] || PATHS.scan}
    </svg>
  );
}
export function Status({ flag }) {
  return (
    <span className="status-pill" data-v={FLAG_TONE[flag]}>
      <Icon name={flag === "normal" ? "check" : "alert"} />
      {FLAG_SHORT[flag]}
    </span>
  );
}
function downloadRecord(leaf) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(leaf.record, null, 2)], {
      type: "application/json",
    }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = leaf.id + "-record.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function PageHeading({ title, description, children }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
export function Dashboard({ leaves, onInspect, onGo }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const flagged = leaves.filter((l) => l.flag !== "normal");
  const feature = leaves[FLAGGED_LEAF];
  const visible = leaves.filter(
    (l) =>
      (filter === "all" ||
        (filter === "flagged" ? l.flag !== "normal" : l.flag === "normal")) &&
      `${l.title} ${l.id} ${l.record.cell_line}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div className="page dashboard">
      <PageHeading
        title="Demo dataset"
        description="Summary of the sample images and their recorded analysis results."
      >
        <button className="button secondary" onClick={() => onGo("audit")}>
          <Icon name="shield" />
          Verify records
        </button>
      </PageHeading>
      <div className="dataset-strip">
        <span className="dataset-icon">
          <Icon name="layers" />
        </span>
        <div>
          <strong>Reference dataset</strong>
          <span>Phase-contrast microscopy · Recorded pipeline results</span>
        </div>
        <span className="dataset-date">
          {leaves[0].record.analysed_at.slice(0, 10)}
        </span>
      </div>
      <div className="summary-grid">
        <Summary
          label="Specimens analysed"
          value={leaves.length}
          detail="Images with bound records"
          icon="scan"
        />
        <Summary
          label="Normal QC"
          value={leaves.length - flagged.length}
          detail="No QC flag raised"
          icon="check"
          tone="normal"
        />
        <Summary
          label="Flagged specimens"
          value={flagged.length}
          detail="Inspect supporting evidence"
          icon="alert"
          tone="amber"
        />
        <Summary
          label="Linked audit records"
          value={leaves.length}
          detail="SHA-256 · verify in your browser"
          icon="shield"
        />
      </div>
      <div className="overview-panels">
        <section className="feature-panel">
          <div className="panel-heading">
            <div>
              <span className="section-label">Inside the analysis</span>
              <h2>From pixels to a QC decision</h2>
            </div>
            <span className="subtle-tag">Recorded example</span>
          </div>
          <div className="feature-content">
            <div className="feature-image">
              <Plate id="overview-plate" leaf={feature} instant fitWidth />
            </div>
            <div className="feature-details">
              <Status flag={feature.flag} />
              <h3>{feature.record.cell_line}</h3>
              <p>{feature.kind}</p>
              <div className="feature-metric">
                <span>Confluency</span>
                <strong>
                  {feature.confluency.toFixed(1)}
                  <small>%</small>
                </strong>
              </div>
              <div className="feature-action">
                <span>Recommended action</span>
                <strong>{ACTION_LABEL[feature.action]}</strong>
              </div>
              <p className="feature-note">
                The highlighted region shows where the QC classifier looked.
              </p>
              <button
                className="text-button"
                onClick={() => onInspect(FLAGGED_LEAF)}
              >
                Inspect specimen
                <Icon name="arrow" />
              </button>
            </div>
          </div>
        </section>
        <section className="distribution-panel">
          <div className="panel-heading">
            <div>
              <span className="section-label">Across this dataset</span>
              <h2>Quality breakdown</h2>
            </div>
          </div>
          <div className="distribution-bars">
            {CLASSES.map((flag) => {
              const count = leaves.filter((l) => l.flag === flag).length;
              return (
                <div className="distribution-row" key={flag}>
                  <div>
                    <span>{FLAG_SHORT[flag]}</span>
                    <strong>
                      {count}
                      <small> / {leaves.length}</small>
                    </strong>
                  </div>
                  <div className="distribution-track">
                    <i
                      data-v={FLAG_TONE[flag]}
                      style={{ width: `${(count / leaves.length) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="distribution-foot">
            <Icon name="layers" />
            <p>
              QC model trained on synthetic data.
              <a href="#/provenance">
                Understand the limitations
                <Icon name="arrow" />
              </a>
            </p>
          </div>
        </section>
      </div>
      <section className="records-panel">
        <div className="panel-heading">
          <div>
            <h2>
              Specimen records{" "}
              <span className="count-label">{leaves.length}</span>
            </h2>
            <p>Select a specimen to explore its image and analysis.</p>
          </div>
          <button className="text-button" onClick={() => onGo("analysis")}>
            Open explorer
            <Icon name="arrow" />
          </button>
        </div>
        <div className="table-toolbar">
          <div className="segmented" role="group" aria-label="Filter specimens">
            {[
              ["all", "All specimens"],
              ["flagged", "Flagged"],
              ["normal", "Normal"],
            ].map(([id, label]) => (
              <button
                key={id}
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="search-field">
            <Icon name="search" />
            <input
              aria-label="Search specimen records"
              placeholder="Search specimens…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        <div
          className="scrollx"
          role="region"
          aria-label="Specimen records"
          tabIndex={0}
        >
          <table className="records-table">
            <thead>
              <tr>
                <th>Specimen</th>
                <th>Cell line</th>
                <th>Confluency</th>
                <th>QC status</th>
                <th>Action</th>
                <th>Record</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((leaf) => (
                <tr key={leaf.id}>
                  <td>
                    <button
                      className="specimen-link"
                      onClick={() => onInspect(leaves.indexOf(leaf))}
                    >
                      <img src={leaf.img} alt="" width="40" height="40" />
                      <span>
                        <strong>{leaf.id}</strong>
                        <small>
                          {leaf.w} × {leaf.h} px
                        </small>
                      </span>
                    </button>
                  </td>
                  <td>{leaf.record.cell_line}</td>
                  <td>
                    <span className="table-confluency">
                      <i style={{ "--value": `${leaf.confluency}%` }} />
                      <span>{leaf.confluency.toFixed(1)}%</span>
                    </span>
                  </td>
                  <td>
                    <Status flag={leaf.flag} />
                  </td>
                  <td>{ACTION_LABEL[leaf.action]}</td>
                  <td>
                    <code>{leaf.record.record_hash.slice(0, 8)}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!visible.length && (
          <div className="empty-search">
            <Icon name="search" />
            <h3>No matching specimens</h3>
            <p>Try a different name or clear the filters.</p>
            <button
              className="button secondary"
              onClick={() => {
                setQuery("");
                setFilter("all");
              }}
            >
              Clear filters
            </button>
          </div>
        )}
        <div className="table-foot">
          Showing {visible.length} of {leaves.length} specimens
          <span>Recorded results · no live inference</span>
        </div>
      </section>
    </div>
  );
}
function Summary({ label, value, detail, icon, tone }) {
  return (
    <div className="summary-item">
      <div>
        <span>{label}</span>
        <Icon name={icon} data-v={tone} />
      </div>
      <strong>{value.toString().padStart(2, "0")}</strong>
      <p>{detail}</p>
    </div>
  );
}
export function Explorer({ leaves, selected, onSelect }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const leaf = leaves[selected];
  const visible = leaves.filter(
    (l) =>
      `${l.id} ${l.title}`.toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" || l.flag !== "normal"),
  );
  const position = visible.indexOf(leaf);
  return (
    <div className="page explorer-page">
      <PageHeading
        title="Cell analysis"
        description="Select a sample to inspect its image, segmentation, and quality results."
      >
        <button
          className="button secondary"
          onClick={() => downloadRecord(leaf)}
        >
          <Icon name="download" />
          Export record
        </button>
      </PageHeading>
      <div className="specimen-toolbar">
        <div>
          <Icon name="scan" />
          <strong>{leaf.record.cell_line}</strong>
          <span>
            {position < 0
              ? "Selected sample outside current filter"
              : `Sample ${position + 1} of ${visible.length}`}
          </span>
        </div>
        <div className="specimen-pager">
          <button
            aria-label="Previous specimen"
            disabled={position <= 0}
            onClick={() => onSelect(leaves.indexOf(visible[position - 1]))}
          >
            <Icon name="chevron" />
            <span>Previous</span>
          </button>
          <button
            aria-label="Next specimen"
            disabled={!visible.length || position === visible.length - 1}
            onClick={() => onSelect(leaves.indexOf(visible[position + 1]))}
          >
            <span>Next</span>
            <Icon name="chevron" />
          </button>
        </div>
      </div>
      <div className="explorer-layout">
        <section className="specimen-library" aria-label="Choose specimen">
          <div className="library-heading">
            <h2>
              Specimens <span>{leaves.length}</span>
            </h2>
            <span className="library-field-label">Find a sample</span>
            <label className="search-field">
              <Icon name="search" />
              <input
                aria-label="Search specimens"
                placeholder="Search specimens…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <select
              aria-label="Filter specimen library"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All QC statuses</option>
              <option value="flagged">Flagged only</option>
            </select>
          </div>
          <div className="specimen-list">
            {visible.map((l) => (
              <button
                key={l.id}
                className="library-item"
                aria-pressed={l === leaf}
                onClick={() => onSelect(leaves.indexOf(l))}
              >
                <img src={l.img} alt="" width="54" height="54" />
                <span>
                  <strong>{l.id}</strong>
                  <small>{l.confluency.toFixed(1)}% confluency</small>
                  <span className="library-status" data-v={FLAG_TONE[l.flag]}>
                    {FLAG_SHORT[l.flag]}
                  </span>
                </span>
              </button>
            ))}
            {!visible.length && (
              <p className="library-empty">
                No specimens match. Try another search or status.
              </p>
            )}
          </div>
        </section>
        <div className="review-panel">
          <div className="viewer-heading">
            <div>
              <h2>{leaf.id}</h2>
              <span>
                {leaf.record.cell_line} · Phase contrast · {leaf.w} × {leaf.h}{" "}
                px
              </span>
            </div>
            <Status flag={leaf.flag} />
          </div>
          <div className="review-image">
            <Plate id="review-plate" leaf={leaf} instant fitWidth />
          </div>
          <div className="image-note">
            <Icon name="scan" />
            <span>
              {leaf.kind}. Segmentation and evidence overlays can be toggled
              independently.
            </span>
          </div>
        </div>
        <Inspector key={leaf.id} leaf={leaf} />
      </div>
    </div>
  );
}
function Inspector({ leaf }) {
  const [tab, setTab] = useState("results");
  const [copy, setCopy] = useState("");
  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(leaf.record.record_hash);
      setCopy("Hash copied");
    } catch {
      setCopy("Copy unavailable. Select the hash below or export the record.");
    }
  };
  return (
    <aside className="inspector" aria-label="Analysis details">
      <div className="inspector-tabs" role="group" aria-label="Detail view">
        {["results", "record"].map((id) => (
          <button key={id} aria-pressed={tab === id} onClick={() => setTab(id)}>
            {id === "results" ? "Analysis results" : "Record"}
          </button>
        ))}
      </div>
      {tab === "results" ? (
        <div className="inspector-content">
          <section className="inspect-section">
            <span className="section-label">Confluency</span>
            <p className="confluency-value">
              {leaf.confluency.toFixed(1)}
              <small>%</small>
            </p>
            <div className="confluency-track">
              <i style={{ width: `${leaf.confluency}%` }} />
              <span style={{ left: "80%" }} />
            </div>
            <div className="metric-caption">
              <span>Cell coverage (Cellpose-SAM)</span>
              <span>Target 80%</span>
            </div>
          </section>
          <section className="inspect-section">
            <span className="section-label">Quality classification</span>
            <h3 data-v={FLAG_TONE[leaf.flag]}>{FLAG_LABEL[leaf.flag]}</h3>
            <p className="confidence-caption">
              {(leaf.qcConf * 100).toFixed(1)}% confidence
            </p>
            <div className="probability-list">
              {CLASSES.map((flag) => (
                <div
                  key={flag}
                  className="probability-row"
                  data-active={flag === leaf.flag}
                >
                  <span>{FLAG_SHORT[flag]}</span>
                  <div>
                    <i style={{ width: `${leaf.probs[flag] * 100}%` }} />
                  </div>
                  <code>{(leaf.probs[flag] * 100).toFixed(1)}%</code>
                </div>
              ))}
            </div>
          </section>
          <section className="inspect-section">
            <span className="section-label">Recommended action</span>
            <div className="action-callout" data-v={ACTION_TONE[leaf.action]}>
              <Icon name={leaf.action === "human_review" ? "alert" : "check"} />
              <strong>{ACTION_LABEL[leaf.action]}</strong>
            </div>
            <p>{leaf.actionReason}</p>
          </section>
          <section className="inspect-section">
            <span className="section-label">Why this decision</span>
            <p>{leaf.rationale}</p>
          </section>
          <button
            className="text-button record-link"
            onClick={() => setTab("record")}
          >
            <Icon name="shield" />
            View the bound record
            <Icon name="arrow" />
          </button>
        </div>
      ) : (
        <div className="inspector-content record-details">
          <section className="inspect-section">
            <h3>Bound analysis record</h3>
            <p>
              Original pipeline output, with image identity and model versions.
            </p>
            <dl>
              {[
                "flask_id",
                "cell_line",
                "analysed_at",
                "schema_version",
                "decided_by",
              ].map((field) => (
                <div key={field}>
                  <dt>{field.replaceAll("_", " ")}</dt>
                  <dd>{String(leaf.record[field])}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="inspect-section">
            <span className="section-label">Record hash · SHA-256</span>
            <code className="full-hash">{leaf.record.record_hash}</code>
            <button className="button secondary" onClick={copyHash}>
              <Icon name="copy" />
              Copy hash
            </button>
            <p role="status">{copy}</p>
          </section>
          <details className="json-details">
            <summary>Full JSON record</summary>
            <pre>{JSON.stringify(leaf.record, null, 2)}</pre>
          </details>
          <a className="text-button record-link" href="#/audit">
            Verify the full chain
            <Icon name="arrow" />
          </a>
        </div>
      )}
    </aside>
  );
}
