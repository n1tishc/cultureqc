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

export function ErrorFigure({ data, letter = "A" }) {
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

export function ReviewFigure({ data, letter = "B" }) {
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
      title="Confluency against expert masks"
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

export function Detectability({ data }) {
  const d = data.detectability;
  const real = row(data, "Anomaly flag vs contamination, bacteria at real size");
  const big = row(data, "Anomaly flag vs contamination (V5)");
  const flagRate = row(data, "Anomaly flag rate, held-out normal");
  return (
    <Section
      id="detectability"
      title="What it can and cannot see"
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
  const kinds = ["pass", "fail", "mixed", "none", "info"].filter((k) => count(k));
  return (
    <Section
      id="checks"
      title={`${v[0].id}–${v[v.length - 1].id}, on held-out data`}
      lede={
        <>
          <p>Every threshold was set on tuning sequences; every result here is on held-out data, with its verdict as scored. Below the table: what the results changed in the product, and what this evidence does not prove.</p>
          <p className="tally" aria-label="Verdicts">
            {kinds.map((k) => (
              <Verdict key={k} k={k}>
                {count(k)} {VERDICT_WORD[k].toLowerCase()}
              </Verdict>
            ))}
          </p>
        </>
      }
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

/* ── release notes ── */

function Note({ title, children, src, was }) {
  return (
    <li className="note">
      <p>
        <b>{title}</b> {children}
      </p>
      {was ? <p className="note-was">In v0.2: {was}</p> : null}
      {src ? (
        <span className="src">
          <Path>{src}</Path>
        </span>
      ) : null}
    </li>
  );
}

export function ReleaseNotes({ data }) {
  const clsSyn = row(data, "QC classifier accuracy, synthetic");
  const clsReal = row(data, "QC classifier on real normal frames");
  const clsRealPct = clsReal.number.match(/^[\d.]+%/)[0];
  const real = row(data, "Anomaly flag vs contamination, bacteria at real size");
  const err = row(data, "Confluency error, Cellpose-SAM");
  const v02 = row(data, "Confluency error, v0.2 headline");
  const cut = row(data, "Confluency error, calibrated cutoff");
  const cutMae = cut.number.match(/MAE ([\d.]+) → ([\d.]+) pp/).slice(1);
  const rev = row(data, "Sent to human review, held-out frames: boundary ambiguity");
  const amb = row(data, "Boundary ambiguity vs the reading's error");
  const fc = row(data, "Passage forecast");
  const spc = row(data, "SPC");
  const flagRate = row(data, "Anomaly flag rate, held-out normal");
  const zg = row(data, "Live latency, console Space on ZeroGPU");
  const ceiling = data.examples.items[0].confluency.ambiguity_ceiling.toFixed(2);
  const nEvican = nums(err.number)[1];
  return (
    <>
      <article className="release" id="v0-3" aria-labelledby="v0-3-h">
        <header className="release-head">
          <h2 id="v0-3-h">v0.3</h2>
          <p>
            Rules <code>{data.meta.rules}</code>
            <br />
            Branch <code>{data.meta.branch}</code>
          </p>
        </header>
        <div className="release-body">
          <section aria-labelledby="new-h">
            <h3 id="new-h">New</h3>
            <ul className="notes">
              <Note title="Per-image anomaly check." src={flagRate.source}>
                DINOv2 patch features of the centre tile, scored against healthy frames of the same confluency, with thresholds set on tuning sequences only. It flags {flagRate.number} of healthy held-out frames, and since rules_v0.3 a flag holds a passage for a person.
              </Note>
              <Note title="Quality gate, flask history and a passage forecast." src={fc.source}>
                Bad images are dropped from the growth trend, and the forecast is backtested at the replays’ passage target: {fc.number}.
              </Note>
              <Note title="A fuller record, verifiable in the browser." src="docs/audit_mapping.md">
                Each record carries the hashes of the image, the probability map, every config and the anomaly bank, the model and rules versions, and the previous record’s hash; an anchored checkpoint catches a rewritten or truncated chain.
              </Note>
              <Note title={`Validation ${data.validation[0].id}–${data.validation[data.validation.length - 1].id} and a detectability matrix.`} src="docs/ARCHITECTURE_VALIDATION.md · configs/detectability.yaml">
                Checks on held-out data with their verdicts as scored, and the matrix’s hash in every record.
              </Note>
              <Note title="A live console." src={zg.source}>
                The same code on a GPU Space, for any image: {zg.number}.
              </Note>
            </ul>
          </section>

          <section aria-labelledby="changed-h">
            <h3 id="changed-h">Changed after testing on real images</h3>
            <ul className="notes">
              <Note title="Confluency error is measured on real images." src={`${err.source} · ${v02.source}`} was={`${v02.number}.`}>
                {err.number}, on {nEvican} held-out EVICAN images with expert masks.
              </Note>
              <Note title="The per-image “confidence” is now “boundary ambiguity”, a review trigger." src={`${amb.source} · ${rev.source}`} was="a per-image confidence.">
                Checked by a rule fixed in advance, the score {amb.number}. Frames above {ceiling} go to a person: {rev.number}.
              </Note>
              <Note title="The QC classifier no longer drives the action." src={`${clsReal.source} · ${clsSyn.source}`} was={`it led the page, with accuracy ${clsSyn.number} on synthetic test tiles.`}>
                It is still recorded in each record, with <code>qc_used_in_decision: false</code>. On real normal frames it called {clsRealPct} normal.
              </Note>
              <Note title="Contamination is listed as not detected here." src={real.source} was="simulated bacteria pasted onto real frames, flagged with evidence boxes.">
                The demo’s bacteria were {data.oversize_factor}× larger than real ones. At their real size: {real.number}.
              </Note>
            </ul>
          </section>

          <section aria-labelledby="next-h">
            <h3 id="next-h">Validated, not yet released</h3>
            <ul className="notes">
              <Note title="A recalibrated cell cutoff for the low reading." src={cut.source}>
                With the cutoff recalibrated on other images, the error on the same {nEvican} images drops from {cutMae[0]} to {cutMae[1]} pp. {data.cutoff_disclosure} It moves the review trigger and the anomaly bins, which are re-derived before it ships.
              </Note>
            </ul>
          </section>

          <section aria-labelledby="kept-h">
            <h3 id="kept-h">Built, kept out of decisions</h3>
            <ul className="notes">
              <Note title="SPC on growth residuals and the instrument-drift monitor." src={spc.source}>
                Both failed validation (SPC: {spc.number}, faults simulated) and stay in code and in the report only.
              </Note>
            </ul>
          </section>
        </div>
      </article>

      <article className="release" id="v0-2" aria-labelledby="v0-2-h">
        <header className="release-head">
          <h2 id="v0-2-h">v0.2</h2>
          <p>
            <a href="https://cultureqc.vercel.app" target="_blank" rel="noreferrer">
              cultureqc.vercel.app <Icon name="external" />
            </a>
          </p>
        </header>
        <div className="release-body">
          <p className="release-p">The first release: Cellpose-SAM confluency, a four-class QC classifier with Grad-CAM evidence boxes, rules for passage, feed and review, and a hash-chained record. Its site is still online. Its headline numbers were measured on synthetic test tiles; v0.3 re-measured them on real images, above.</p>
        </div>
      </article>
    </>
  );
}
