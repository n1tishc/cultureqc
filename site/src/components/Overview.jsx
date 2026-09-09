import LadderCell from "./LadderCell";
import { FLAGGED_LEAF } from "../lib/labels";

/* The four sections after the hero. They are pure content with one data-bound
   field each, so they live together rather than in four files of boilerplate. */

const OUTPUTS = [
  [
    "Confluency",
    "A percentage of the field covered by cells, from a segmentation probability map rather than a brightness cut, so it survives a change of cell line.",
    "confluency_pct",
    (d) => d.confluency.toFixed(2),
  ],
  [
    "Flag with evidence",
    "One of normal, contamination suspected, detachment or image quality, with up to eight Grad-CAM regions marking the pixels that drove it.",
    "qc_flag",
    (d) => d.flag.replace("_", "_​"),
  ],
  [
    "Recommended action",
    "Passage, feed, hold or human review, decided by an explicit rules engine over the numbers — never by the model itself.",
    "recommended_action",
    (d) => d.action,
  ],
  [
    "Audit record",
    "One canonical JSON line, SHA-256 hashed and linked to the previous line, carrying model versions and the image's own hash.",
    "record_hash",
    (d) => d.record.record_hash.slice(0, 24) + "…",
  ],
];

export function Outputs({ leaves }) {
  const d = leaves[FLAGGED_LEAF];
  return (
    <section className="sec invert" id="sec-outputs">
      <div className="sechead rv">
        <h2>Four outputs, bound together.</h2>
        <span className="docaddr">Pipeline &middot; analyze()</span>
      </div>
      <p className="lede rv">
        One call returns all four, written into the same record, so the number,
        the evidence, the decision and the proof cannot drift apart.
      </p>
      <div className="schedule rv" id="schedule">
        {OUTPUTS.map(([title, body, key, fn]) => (
          <div className="srow" key={key}>
            <div>
              <h3>{title}</h3>
            </div>
            <div>
              <p>{body}</p>
            </div>
            <div className="sfield">
              <span className="k">{key}</span>
              <span className={"v" + (key === "record_hash" ? " hash" : "")}>
                {fn(d)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Measure({ onGo }) {
  return (
    <section className="sec" id="sec-measure">
      <div className="sechead major rv">
        <h2>Thresholding measures brightness. Confluency is not brightness.</h2>
        <span className="docaddr">Confluency &middot; zero-shot</span>
      </div>
      <div className="headtohead rv">
        <div className="hh win">
          <p className="hhnum">
            2.3<small>pp</small>
          </p>
          <p className="hhname">cultureQC</p>
        </div>
        <div className="hh">
          <p className="hhnum">
            31<small>pp</small>
          </p>
          <p className="hhname">Classical thresholding</p>
        </div>
      </div>

      <figure className="errscale rv">
        <figcaption>
          Mean absolute confluency error, zero-shot across morphologies &middot;
          same benchmark, same images &middot; bars to scale &middot;{" "}
          <b className="stated">evaluation figure, not recomputed here</b>
        </figcaption>
        <div className="esrow">
          <span className="esname">cultureQC</span>
          <span className="estrack">
            <span className="esbar win" style={{ "--w": "7.4%" }}></span>
          </span>
          <span className="esval">
            2.3<i>pp</i>
          </span>
        </div>
        <div className="esrow">
          <span className="esname">Thresholding</span>
          <span className="estrack">
            <span className="esbar" style={{ "--w": "100%" }}></span>
          </span>
          <span className="esval">
            31<i>pp</i>
          </span>
        </div>
        <div className="esrow esaxisrow" aria-hidden="true">
          <span></span>
          <span className="estick">
            <b>0</b>
            <b>31 pp</b>
          </span>
          <span></span>
        </div>
      </figure>

      <p className="foot rv">
        Thirteen times the error &mdash; the difference between passaging and
        doing nothing. Both methods run on four real fields in{" "}
        <a
          href="#/analysis"
          className="xlink"
          onClick={(e) => {
            e.preventDefault();
            onGo("analysis");
          }}
        >
          the analysis view
        </a>
        .
      </p>
    </section>
  );
}

export function Recall({ ladder, onGo }) {
  return (
    <section className="sec" id="sec-recall">
      <div className="sechead rv">
        <h2>Contamination is only useful to catch early.</h2>
        <span className="docaddr">QC classifier &middot; recall</span>
      </div>
      <p className="lede rv">
        Late contamination is obvious to anyone. The rung that matters is the
        first few dozen organisms in the field, long before turbidity shows in
        the flask.{" "}
        <strong>
          98% test accuracy, 100% contamination recall at every severity
          including early.
        </strong>{" "}
        <span className="stated">
          Evaluation figures, not recomputed on this page &mdash; see{" "}
          <a href="#/analysis">provenance</a>.
        </span>
      </p>
      <div className="ladstrip rv" id="ladstrip">
        {["clean", "early", "mid", "late"].map((sev) => (
          <LadderCell
            key={sev}
            sev={sev}
            line="Huh7"
            cell={ladder.find((x) => x.line === "Huh7" && x.sev === sev)}
          />
        ))}
      </div>
      <p className="foot rv">
        One row of the severity matrix. The full four-line grid is in{" "}
        <a
          href="#/analysis"
          className="xlink"
          onClick={(e) => {
            e.preventDefault();
            onGo("analysis");
          }}
        >
          the analysis view
        </a>
        .
      </p>
    </section>
  );
}

export function Integrate() {
  return (
    <section className="sec" id="sec-integrate">
      <div className="sechead rv">
        <h2>Software, not an instrument.</h2>
        <span className="docaddr">Integration surface</span>
      </div>
      <div className="split">
        <div className="rv">
          <ul className="notlist">
            <li>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                aria-hidden="true"
              >
                <rect x="3" y="4" width="18" height="16" rx="1" />
                <path d="M3 9h18M8 4v16" strokeLinecap="round" />
              </svg>
              <div>
                <b>Vendor-neutral input</b>
                <span>
                  A grayscale brightfield or phase-contrast image. No proprietary
                  capture format, no required optics vendor.
                </span>
              </div>
            </li>
            <li>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                aria-hidden="true"
              >
                <path
                  d="M12 3v18M5 8l7-5 7 5M5 16l7 5 7-5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div>
                <b>Deterministic record out</b>
                <span>
                  One canonical JSON line per call, hashed and linked to the line
                  before it, with model versions travelling alongside.
                </span>
              </div>
            </li>
            <li>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                aria-hidden="true"
              >
                <path
                  d="M12 3l8 3v6c0 4.4-3.2 7.9-8 9-4.8-1.1-8-4.6-8-9V6l8-3z"
                  strokeLinejoin="round"
                />
                <path
                  d="M9 12l2.2 2.2L15.5 10"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div>
                <b>Built for the audit</b>
                <span>
                  The schema is designed against what 21&nbsp;CFR&nbsp;Part&nbsp;11
                  §11.10(e) asks for — to map onto a validated system, not to
                  substitute for one.
                </span>
              </div>
            </li>
          </ul>
        </div>
        <pre className="code rv">
          <code>
            <span className="c"># one image in, one auditable record out</span>
            {"\n"}
            <span className="k">from</span> culture.pipeline{" "}
            <span className="k">import</span> analyze{"\n\n"}
            record = <span className="k">analyze</span>({"\n    "}
            <span className="s">&quot;flask_A12_02d16h.tif&quot;</span>,{"\n    "}
            flask_id=<span className="s">&quot;F-00291&quot;</span>,{"\n    "}
            cell_line=<span className="s">&quot;Huh7&quot;</span>,{"\n    "}
            log_path=<span className="s">&quot;events.jsonl&quot;</span>,{"\n"})
            {"\n\n"}
            record[<span className="s">&quot;confluency_pct&quot;</span>]
            {"        "}
            <span className="c">
              # <span className="n">35.23</span>
            </span>
            {"\n"}
            record[<span className="s">&quot;qc_flag&quot;</span>]{"               "}
            <span className="c">
              # <span className="n">&quot;normal&quot;</span>
            </span>
            {"\n"}
            record[<span className="s">&quot;qc_evidence_bbox&quot;</span>]
            {"      "}
            <span className="c">
              # <span className="n">[x, y, w, h]</span>
            </span>
            {"\n"}
            record[<span className="s">&quot;recommended_action&quot;</span>]
            {"    "}
            <span className="c">
              # <span className="n">&quot;feed&quot;</span>
            </span>
            {"\n"}
            record[<span className="s">&quot;prev_record_hash&quot;</span>]
            {"      "}
            <span className="c">
              # <span className="n">links to the line before</span>
            </span>
            {"\n"}
            record[<span className="s">&quot;record_hash&quot;</span>]
            {"           "}
            <span className="c">
              # <span className="n">sha-256 of this line</span>
            </span>
          </code>
        </pre>
      </div>
    </section>
  );
}
