import { Fig, Icon, Path, Section, Verdict } from "./ui";

/* Every number below is looked up from data.json, which build_data.py copies
   from the README tables (checked against their sources by the test suite),
   configs/detectability.yaml and results/review_rate.csv. */

export const row = (data, prefix) => {
  const r = data.results.find((x) => x.result.startsWith(prefix));
  if (!r) throw new Error(`results row not found: ${prefix}`);
  return r;
};

const nums = (s) => (s.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);

function Src({ children }) {
  return <Path>{children}</Path>;
}

/* ── confluency ── */

function ErrorFigure({ data }) {
  const r = row(data, "Confluency error, Cellpose-SAM");
  const v1 = data.validation.find((v) => v.id === "V1");
  const [mae, n, base] = nums(r.number);
  const max = Math.ceil(Math.max(mae, base) / 5) * 5;
  const bars = [
    ["Cellpose-SAM", mae, "var(--cell-ink)"],
    ["Threshold baseline", base, "var(--rule-2)"],
  ];
  return (
    <Fig
      letter="A"
      title="Error against expert masks"
      legend={
        <>
          Mean absolute error in percentage points, n = {n} EVICAN images (real). {v1.result}. Source: <Src>{r.source}</Src>.
        </>
      }
    >
      <div className="bars">
        {bars.map(([label, value, color]) => (
          <div className="bars-row" key={label}>
            <span>{label}</span>
            <span className="track">
              <i style={{ width: `${(value / max) * 100}%`, background: color, opacity: 1 }} />
            </span>
            <span className="v">{value.toFixed(2)} pp</span>
          </div>
        ))}
      </div>
    </Fig>
  );
}

function ReviewFigure({ data }) {
  const rr = data.review_rate;
  const all = rr.find((r) => r.group === "C2C12 held-out, full frames");
  const bins = rr.filter((r) => /^C2C12 held-out, confluency/.test(r.group));
  const max = Math.max(...bins.map((b) => b.pct), 10);
  const ceiling = data.examples.items[0].confluency.ambiguity_ceiling;
  const worst = bins.reduce((a, b) => (b.pct > a.pct ? b : a)).group.replace("C2C12 held-out, confluency ", "");
  return (
    <Fig
      letter="B"
      title="Where the ambiguity trigger sends frames to review"
      legend={
        <>
          Held-out C2C12 frames with boundary ambiguity above {ceiling.toFixed(2)}, by confluency. Overall {all.pct}% of {all.n} frames ({all.sequences} sequences). The score rises with density, so review piles up in the {worst} band, where passage decisions are made; it is a review trigger, not a measure of the reading’s error. Source: <Src>results/review_rate.csv</Src>.
        </>
      }
    >
      <div className="bars">
        {bins.map((b) => (
          <div className="bars-row" key={b.group}>
            <span>{b.group.replace("C2C12 held-out, confluency ", "")}</span>
            <span className="track">
              <i data-zero={b.pct === 0 ? "" : undefined} style={{ width: `${(b.pct / max) * 100}%` }} />
            </span>
            <span className="v">
              {b.pct.toFixed(1)}% of {b.n}
            </span>
          </div>
        ))}
      </div>
    </Fig>
  );
}

function NoiseFigure({ data }) {
  const r = row(data, "FOV sampling noise");
  const field = r.result.split(", ").slice(1).join(", ");
  const n = data.replays[0].visits[0].fov.length;
  const v2 = data.validation.find((v) => v.id === "V2");
  const [a, b] = nums(r.number.split("=")[1]);
  const W = 300;
  const H = 150;
  const m = { l: 34, r: 8, t: 10, b: 24 };
  const xs = [0, 20, 40, 60, 80];
  const ymax = Math.ceil((a + b * 80) / 5) * 5;
  const X = (c) => m.l + (c / 80) * (W - m.l - m.r);
  const Y = (s) => H - m.b - (s / ymax) * (H - m.t - m.b);
  return (
    <Fig
      letter="C"
      title="How much one field of view wobbles"
      legend={
        <>
          σ between fields of the same C2C12 frame ({field}): {r.number}. A visit averages {n} fields. V2: {v2.result} ({v2.verdict}). Source: <Src>{r.source}</Src>.
        </>
      }
    >
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }} role="img" aria-label={`FOV noise rises from ${a} to ${(a + b * 80).toFixed(1)} percentage points between 0 and 80% confluency`}>
        {[0, ymax / 2, ymax].map((t) => (
          <g key={t}>
            <line x1={m.l} x2={W - m.r} y1={Y(t)} y2={Y(t)} stroke="var(--rule)" />
            <text x={m.l - 6} y={Y(t) + 3.5} textAnchor="end" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-3)">
              {t}
            </text>
          </g>
        ))}
        {xs.map((c) => (
          <text key={c} x={X(c)} y={H - 7} textAnchor="middle" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-3)">
            {c}%
          </text>
        ))}
        <line x1={X(0)} y1={Y(a)} x2={X(80)} y2={Y(a + b * 80)} stroke="var(--cell-ink)" strokeWidth="2" />
        <line x1={X(0)} y1={Y(a / Math.sqrt(n))} x2={X(80)} y2={Y((a + b * 80) / Math.sqrt(n))} stroke="var(--cell-ink)" strokeWidth="1.5" strokeDasharray="4 3" />
        <text x={X(80)} y={Y(a + b * 80) - 6} textAnchor="end" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-2)">
          1 field
        </text>
        <text x={X(80)} y={Y((a + b * 80) / Math.sqrt(n)) + 26} textAnchor="end" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-2)">
          mean of {n} (÷√{n})
        </text>
      </svg>
    </Fig>
  );
}

export function Confluency({ data }) {
  const ceiling = data.examples.items[0].confluency.ambiguity_ceiling;
  return (
    <Section
      id="confluency"
      title="How far to trust one confluency reading"
      lede={
        <p>
          Cellpose-SAM’s probability map gives the number; the share of pixels close to its cutoff gives the boundary ambiguity, and a frame above {ceiling.toFixed(2)} goes to a person. Both were measured on real images: the number against expert masks, and the ambiguity against the number’s error, which it does not predict. It tracks density, so it is a review trigger, not a confidence.
        </p>
      }
    >
      <div className="figs g3">
        <ErrorFigure data={data} />
        <ReviewFigure data={data} />
        <NoiseFigure data={data} />
      </div>
    </Section>
  );
}

/* ── limits ── */

function detectKind(text) {
  const t = text.toLowerCase();
  if (t.startsWith("yes")) return ["pass", "Yes"];
  if (t.startsWith("not tested")) return ["untested", "Not tested"];
  if (t.startsWith("not reliably")) return ["mixed", "Not reliably"];
  return ["fail", "No"];
}

export function Limits({ data }) {
  const d = data.detectability;
  const real = row(data, "Anomaly flag vs contamination, bacteria at real size");
  const big = row(data, "Anomaly flag vs contamination (V5)");
  const flagRate = row(data, "Anomaly flag rate, held-out normal");
  return (
    <Section
      id="limits"
      title="What it cannot see, stated before anyone asks"
      lede={
        <>
          <p>Each fault type has a row: what was tested, on what, and what to confirm it with. The matrix’s SHA-256 is in every record, so a reading can be traced to the limits that applied when it was made.</p>
          <p className="sources">
            {d.tested_setup} Source: <Src>configs/detectability.yaml</Src>.
          </p>
        </>
      }
    >
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Detectability matrix">
        <table>
          <thead>
            <tr>
              <th scope="col">Issue</th>
              <th scope="col">Detectable here</th>
              <th scope="col">Evidence</th>
              <th scope="col">Confirm with</th>
            </tr>
          </thead>
          <tbody>
            {d.rows.map((r) => {
              const [k, word] = detectKind(r.detectable_here);
              return (
                <tr key={r.issue}>
                  <td>{r.issue}</td>
                  <td style={{ minWidth: 220 }}>
                    <Verdict k={k}>{word}</Verdict>
                    {r.detectable_here.toLowerCase() !== word.toLowerCase() ? <span className="verdict-note">{r.detectable_here}</span> : null}
                  </td>
                  <td style={{ fontSize: 13.5, minWidth: 280 }}>{r.evidence}</td>
                  <td>{r.confirm_with}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="figs g-limits" style={{ marginTop: 16 }}>
        <Fig
          letter="A"
          title="The same bacteria, oversized and at real size"
          legend={
            <>
              The anomaly check’s {data.examples.items[0].anomaly.tile.size} px centre tile of one late held-out frame. Left to right: no fault; the stress test (bacteria {data.oversize_factor}× too large, as pasted in v0.2); the same bacteria at real size, with and without the simulator’s haze. Source: <Src>results/contamination_scale.md</Src>.
            </>
          }
        >
          <div className="panels" aria-hidden="true">
            <span>No fault</span>
            <span>{data.oversize_factor}× too large</span>
            <span>Real size, haze</span>
            <span>Real size, no haze</span>
          </div>
          <img className="figure-img" src={data.contamination_figure} alt={`Four versions of one 256-pixel tile: no bacteria, bacteria pasted ${data.oversize_factor} times too large, and the same bacteria at their real size with and without haze.`} />
        </Fig>
        <Fig letter="B" title="What the numbers say">
          <dl className="fields">
            <dt>Real size</dt>
            <dd>
              {real.number} <br />
              <Src>{real.source}</Src>
            </dd>
            <dt>{data.oversize_factor}× too large</dt>
            <dd>
              {big.number} <br />
              <Src>{big.source}</Src>
            </dd>
            <dt>Normal frames</dt>
            <dd>
              Flagged {flagRate.number} <br />
              <Src>{flagRate.source}</Src>
            </dd>
          </dl>
          <p className="legend">
            At real size the per-visit flag is at chance, so the passage hold gives no protection against contamination at this magnification. Confirm contamination by culture, Gram stain or PCR.
          </p>
        </Fig>
      </div>
    </Section>
  );
}

/* ── validation ── */

const VERDICT_WORD = { pass: "Pass", fail: "Fail", mixed: "Mixed", none: "No verdict", info: "Informational" };

export function Validation({ data }) {
  const v = data.validation;
  const count = (k) => v.filter((x) => x.kind === k).length;
  return (
    <Section
      id="validation"
      title={`${v.length} validation checks, ${count("fail")} of them failed`}
      lede={<p>{data.validation_intro}</p>}
    >
      <div className="table-wrap" tabIndex={0} role="region" aria-label="Validation checks V1 to V10">
        <table>
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col">Held-out result</th>
              <th scope="col">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {v.map((x) => (
              <tr key={x.id}>
                <td style={{ minWidth: 220 }}>
                  <span className="vid">{x.id}</span>
                  {x.check}
                </td>
                <td style={{ minWidth: 300 }}>{x.result}</td>
                <td style={{ minWidth: 180 }}>
                  <Verdict k={x.kind}>{VERDICT_WORD[x.kind]}</Verdict>
                  {x.verdict.toLowerCase() !== VERDICT_WORD[x.kind].toLowerCase() ? <span className="verdict-note">{x.verdict}</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="figs g2" style={{ marginTop: 16 }}>
        <Fig title="What changed because of it">
          <ul style={{ margin: 0, paddingLeft: 18, color: "var(--ink-2)", fontSize: 14.5, lineHeight: 1.6, display: "grid", gap: 8 }}>
            {data.decisions.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </Fig>
        <Fig title="What this does not prove">
          <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14.5, lineHeight: 1.6 }}>
            {data.not_proven} Full report: <Src>docs/ARCHITECTURE_VALIDATION.md</Src>.
          </p>
        </Fig>
      </div>
    </Section>
  );
}

/* ── integration ── */

export function Integration({ data }) {
  const lat = data.results.filter((r) => r.result.startsWith("Live latency"));
  const label = (r) =>
    r.result.includes("ZeroGPU") ? "Console Space, ZeroGPU" : r.result.includes("T4") ? "Colab, Tesla T4" : r.result.includes("Mac") ? "Mac, Apple MPS" : "CPU, 2 threads (V9)";
  return (
    <Section
      id="integration"
      title="One call per image, one line per record"
      lede={
        <p>
          <code>analyze()</code> reads the image, runs Cellpose-SAM, the anomaly check and the rules, and appends the record to an append-only, hash-chained log. The quality gate, flask history and passage forecast run per visit on top of it.
        </p>
      }
    >
      <div className="int-grid">
        <pre className="code" tabIndex={0} aria-label="Python example">
          <span className="k">from</span> culture.pipeline <span className="k">import</span> <span className="f">analyze</span>
          {"\n\n"}rec = <span className="f">analyze</span>(
          {"\n    "}image_path,
          {"\n    "}flask_id=<span className="s">"A12"</span>,
          {"\n    "}cell_line=<span className="s">"C2C12"</span>,
          {"\n    "}hours_since_passage=hours,
          {"\n    "}log_path=<span className="s">"records.jsonl"</span>,  <span className="c"># append-only, hash-chained</span>
          {"\n"})
          {"\n\n"}rec[<span className="s">"confluency_pct"</span>], rec[<span className="s">"confluency_confidence"</span>]
          {"\n"}rec[<span className="s">"anomaly_flag"</span>], rec[<span className="s">"recommended_action"</span>]
          {"\n"}rec[<span className="s">"record_hash"</span>]  <span className="c"># links to the previous record</span>
        </pre>
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Where it runs and how fast">
          <table>
            <thead>
              <tr>
                <th scope="col">Where it runs</th>
                <th scope="col">Per frame</th>
              </tr>
            </thead>
            <tbody>
              {lat.map((r) => (
                <tr key={r.result}>
                  <td>{label(r)}</td>
                  <td>
                    {r.number}
                    <span className="verdict-note">
                      <Src>{r.source}</Src>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  );
}

/* ── what changed since v0.2 ── */

export function Changes({ data }) {
  const clsSyn = row(data, "QC classifier accuracy, synthetic");
  const clsReal = row(data, "QC classifier on real normal frames");
  const real = row(data, "Anomaly flag vs contamination, bacteria at real size");
  const err = row(data, "Confluency error, Cellpose-SAM");
  const v02 = row(data, "Confluency error, v0.2 headline");
  const cut = row(data, "Confluency error, calibrated cutoff");
  const cutMae = cut.number.match(/MAE ([\d.]+) → ([\d.]+) pp/).slice(1);
  const rev = row(data, "Sent to human review, held-out frames: boundary ambiguity");
  const amb = row(data, "Boundary ambiguity vs the reading's error");
  const fc = row(data, "Passage forecast");
  const spc = row(data, "SPC");
  const items = [
    {
      was: `Confluency error ${v02.number}.`,
      now: (
        <>
          <b>Measured on real images instead:</b> {err.number}, on 33 held-out EVICAN images with expert masks. The v0.2 numbers did not hold on real images.
        </>
      ),
      src: `${v02.source} · ${err.source}`,
    },
    {
      was: "The QC classifier led the page: its accuracy and contamination recall, measured on synthetic test tiles.",
      now: (
        <>
          <b>Demoted.</b> On synthetic tiles: {clsSyn.number}. On real held-out C2C12 normal frames it calls {clsReal.number}. It is still recorded, never used for the action.
        </>
      ),
      src: clsReal.source,
    },
    {
      was: "Contamination shown as DeepBacs bacteria pasted onto real frames, flagged with evidence boxes.",
      now: (
        <>
          <b>Those bacteria were {data.oversize_factor}× too large.</b> At their real size: {real.number}. Contamination is now listed as not detected here.
        </>
      ),
      src: real.source,
    },
    {
      was: "Confluency with a per-image confidence.",
      now: (
        <>
          <b>The “confidence” is now “boundary ambiguity”.</b> Checked by a rule fixed in advance, the per-image score {amb.number}. So it is shown as a review trigger, not a confidence. Frames above {data.examples.items[0].confluency.ambiguity_ceiling.toFixed(2)} go to review: {rev.number}.
        </>
      ),
      src: `${amb.source} · ${rev.source}`,
    },
    {
      was: "Not in v0.2.",
      kept: true,
      now: (
        <>
          <b>A fix for the low reading, validated and held for release.</b> Most of it comes from the model’s cell cutoff. With the cutoff recalibrated on other images, the error on the same 33 images drops from {cutMae[0]} to {cutMae[1]} pp. {data.cutoff_disclosure} It is not live yet: it moves the review trigger and the anomaly bins, which are re-derived first.
        </>
      ),
      src: cut.source,
    },
    {
      was: "Not in v0.2.",
      kept: true,
      now: (
        <>
          <b>Per-image anomaly check, quality gate, flask history and a passage forecast.</b> Forecast backtest at the replays’ passage target: {fc.number}. Since rules_v0.3 an anomaly flag holds a passage for human review.
        </>
      ),
      src: fc.source,
    },
    {
      was: "Not in v0.2.",
      kept: true,
      now: (
        <>
          <b>Validated V1–V10, fails stated,</b> and a detectability matrix whose hash rides in every record, next to the hashes of the probability map and configs, and the model names.
        </>
      ),
      src: "docs/ARCHITECTURE_VALIDATION.md · configs/detectability.yaml",
    },
    {
      was: "Not in v0.2.",
      kept: true,
      now: (
        <>
          <b>Built, failed validation, kept out of decisions:</b> SPC on growth residuals ({spc.number}) and the instrument-drift monitor.
        </>
      ),
      src: spc.source,
    },
  ];
  return (
    <Section
      id="changes"
      title="What changed since v0.2"
      lede={
        <p>
          The v0.2 site is still up at{" "}
          <a href="https://cultureqc.vercel.app" target="_blank" rel="noreferrer">
            cultureqc.vercel.app
          </a>
          . Here is what it showed, and what testing on real images changed.
        </p>
      }
    >
      <div className="changes" role="table" aria-label="v0.2 against v0.3">
        <div className="change change-head" role="row">
          <div role="columnheader">What v0.2 showed</div>
          <div role="columnheader">v0.3, after testing on real images</div>
        </div>
        {items.map((c, i) => (
          <div className="change" key={i} role="row">
            <div role="cell">
              <p className={c.kept ? "kept" : ""}>{c.was}</p>
            </div>
            <div role="cell">
              <p>{c.now}</p>
              <span className="src">
                <Path>{c.src}</Path>
              </span>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

export function Footer({ data, commit }) {
  const credits = [...new Set(data.examples.items.map((e) => e.credit))];
  return (
    <footer className="foot">
      <div className="wrap foot-grid">
        <div>
          <h4>cultureQC v0.3</h4>
          <p>
            Every figure on this page is generated from the repository’s stored output by <code>site/assets/build_data.py</code>; the numbers come from the README tables that <code>tests/test_readme_provenance.py</code> checks against their source files.
          </p>
          <p>
            Built from <code>{data.meta.branch}</code>
            {commit ? (
              <>
                {" "}
                at <code>{commit.slice(0, 7)}</code>
              </>
            ) : null}
            .
          </p>
        </div>
        <div>
          <h4>Images</h4>
          {credits.map((c) => (
            <p key={c}>{c}</p>
          ))}
        </div>
        <div>
          <h4>Links</h4>
          <p>
            <a href={data.meta.console_url} target="_blank" rel="noreferrer">
              Live console <Icon name="external" />
            </a>
          </p>
          <p>
            <a href={data.meta.repo_url} target="_blank" rel="noreferrer">
              Source repository
            </a>
          </p>
          <p>
            <a href="https://cultureqc.vercel.app" target="_blank" rel="noreferrer">
              The v0.2 site
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
