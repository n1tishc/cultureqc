import { Fig, Icon, Linked, Path, Section, Verdict } from "./ui";

/* Every number below is looked up from data.json, which build_data.py copies
   from the README tables (checked against their sources by the test suite),
   configs/detectability.yaml, results/review_rate.csv and results/review_rate_v05.csv. */

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
  const rescored = row(data, "Confluency error, EVICAN calibration profile").number.match(/MAE ([\d.]+) →/)[1];
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
          Mean absolute error in percentage points, n = {n} EVICAN images (real). <Linked>{v1.result}</Linked>. The calibration study scored the same {n} images again in a separate run: {rescored} pp at this cutoff. Source: <Src>{r.source}</Src>.
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
      title="Where rules_v0.4’s ambiguity trigger sent frames to review"
      legend={
        <>
          Held-out C2C12 frames with boundary ambiguity above {ceiling.toFixed(2)}, by confluency, under rules_v0.4: {all.pct}% of {all.n} overall ({all.sequences} sequences). The score rises with density, so review piled up in the {worst} band, where passage is decided. Source: <Src>results/review_rate.csv</Src>.
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
          At Cellpose-SAM’s default cutoff, before any calibration. Boundary ambiguity, the share of pixels close to the cutoff, tracks density rather than the reading’s error: rules_v0.4 sent frames above {ceiling.toFixed(2)} to a person; since rules_v0.5 it is recorded but no longer decides, and the calibrated error bands above took its place.
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
      title="Detection scope and next improvements"
      lede={
        <>
          <p><strong>Working checks:</strong> the image-quality gate catches the tested blur, exposure and uneven-illumination defects. In held-out C2C12 replay it also rejects 12.1% of normal frames, so tuning on the target instrument is still needed. <Src>results/quality_gate_c2c12.md</Src>.</p>
          <p><strong>Further improvements:</strong> realistic-scale simulated bacterial contamination was not detected in this setup, and the temporal monitor flagged 0 of 2 simulated growth stalls. Neither an unflagged image nor a confluency reading clears a culture of contamination. <Src>results/contamination_scale.md</Src> · <Src>results/spc_summary.md</Src>.</p>
          <p>Keep biological confirmation separate from image QC. The full detection matrix and supporting experiments remain available below; its SHA-256 is recorded with each analysis.</p>
          <p className="sources">
            {/* The matrix is hashed into every record, so its wording stays; only this display says "quarter-frame". */}
            {d.tested_setup.replace("0.25-frac fields of view", "quarter-frame fields of view")} Source: <Src>configs/detectability.yaml</Src>.
          </p>
        </>
      }
    >
      <details className="more-details">
        <summary>Full detection scope and supporting experiments</summary>
        <p>The original architecture-test protocols and outcomes remain in <Src>docs/ARCHITECTURE_VALIDATION.md</Src>. They are historical experiments, not a current product scorecard.</p>
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
                  <td style={{ fontSize: 13.5, minWidth: 280 }}>
                    <Linked>{r.evidence}</Linked>
                  </td>
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
      </details>
    </Section>
  );
}

/* ── validation ── */

const VERDICT_WORD = { pass: "Pass", fail: "Fail", mixed: "Mixed", none: "No verdict", info: "Informational" };

export function Validation({ data }) {
  const v = data.validation;
  const first = data.results.find((r) => r.result.startsWith("Live latency, console Space on ZeroGPU, first run"));
  const warm = data.results.find((r) => r.result.startsWith("Live latency, console Space on ZeroGPU, second run"));
  const count = (k) => v.filter((x) => x.kind === k).length;
  const kinds = ["pass", "fail", "mixed", "none", "info"].filter((k) => count(k));
  return (
    <Section
      id="checks"
      title={`${v[0].id}–${v[v.length - 1].id}: the architecture tests`}
      lede={
        <>
          <p>
            Recorded C2C12 sequences were split into tuning and held-out groups, then replayed with simulated visits and faults. The table also includes a separate EVICAN mask comparison, synthetic classifier tiles and a CPU latency test. Each verdict applies to its stated test; it is not evidence of production operation. Protocols, sample counts and source reports: <Src>docs/ARCHITECTURE_VALIDATION.md</Src>.
          </p>
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
                <td style={{ minWidth: 300 }}>
                  <Linked>{x.result}</Linked>
                </td>
                <td style={{ minWidth: 180 }}>
                  <Verdict k={x.kind}>{VERDICT_WORD[x.kind]}</Verdict>
                  {x.verdict.toLowerCase() !== VERDICT_WORD[x.kind].toLowerCase() ? <span className="verdict-note">{x.verdict}</span> : null}
                  {x.id === "V9" && warm ? (
                    <span className="verdict-note">
                      Measured on CPU. On the GPU console a live analysis took a median {nums(first.number)[0]} s in the first run after a restart and {nums(warm.number)[0]} s in the second (see Integration).
                    </span>
                  ) : null}
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
              <li key={d}>
                <Linked>{d}</Linked>
              </li>
            ))}
          </ul>
        </Fig>
        <Fig title="What this does not prove">
          <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14.5, lineHeight: 1.6 }}>
            <Linked>{data.not_proven}</Linked> Full report: <Src>docs/ARCHITECTURE_VALIDATION.md</Src>.
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
    r.result.includes("ZeroGPU, first run")
      ? "Console Space, ZeroGPU, first run after a restart"
      : r.result.includes("ZeroGPU, second run")
        ? "Console Space, ZeroGPU, second run"
        : r.result.includes("T4")
          ? "Colab, Tesla T4; before calibration profiles"
          : r.result.includes("Mac")
            ? "Mac, Apple GPU (MPS)"
            : "CPU, 2 threads; tiled LIVECell fixture (V9)";
  const timingProtocol = (result) =>
    result.includes("ZeroGPU")
      ? null
      : result.includes("T4") || result.includes("Mac")
        ? "Median across 5 distinct C2C12 example images after one untimed warm-up pass; models resident, model loading excluded."
        : "Median of 2 timed runs per input after warm-up; models resident, model loading excluded.";
  return (
    <Section
      id="integration"
      title="An image and context in. A record for the host out."
      lede={
        <>
          <p>The current integration surface is the Python function <code>culture.pipeline.analyze()</code>. It reads an image, applies the selected profile’s quality gate when available, computes confluency and anomaly evidence, applies the rules, and appends a reading to a local hash-chained log.</p>
          <p>This is a designed host boundary, not a deployed platform integration or a hosted API contract. The caller owns capture, scheduling, identity and signatures, durable audit retention, and every physical action.</p>
        </>
      }
    >
      <dl className="fields">
        <dt>You supply</dt>
        <dd>An image path, vessel and imaging identifiers, the matching calibration profile, and timing or policy inputs. The example uses the repository’s MSC profile; it is not a profile for a new partner microscope.</dd>
        <dt>You receive</dt>
        <dd>A confluency reading and available error band, a recommendation with its reason, any re-image request, provenance hashes and the appended record’s hash. A recommendation is for host review; it does not actuate equipment.</dd>
        <dt>The host retains</dt>
        <dd>The images and related artifacts, a checkpoint outside the log, authenticated review and approval records, and responsibility for system validation. A local JSONL file is not a complete durable audit service.</dd>
      </dl>
      <p>Example Python call, with <code>image_path</code> and <code>hours</code> supplied by the caller and the configured models available:</p>
      <div className="int-grid">
        <pre className="code" tabIndex={0} aria-label="Python example">
          <span className="k">from</span> culture.pipeline <span className="k">import</span> <span className="f">analyze</span>
          {"\n\n"}rec = <span className="f">analyze</span>(
          {"\n    "}image_path,
          {"\n    "}flask_id=<span className="s">"A12"</span>,
          {"\n    "}cell_line=<span className="s">"MSC"</span>,
          {"\n    "}profile_id=<span className="s">"msc_phase"</span>,  <span className="c"># the imaging setup's calibration</span>
          {"\n    "}imager_id=<span className="s">"imager-1"</span>,
          {"\n    "}hours_since_passage=hours,
          {"\n    "}log_path=<span className="s">"records.jsonl"</span>,  <span className="c"># append-only, hash-chained</span>
          {"\n"})
          {"\n\n"}rec[<span className="s">"confluency_pct"</span>], rec[<span className="s">"confluency_interval"</span>]  <span className="c"># reading, 90% error band</span>
          {"\n"}rec[<span className="s">"recommended_action"</span>], rec[<span className="s">"action_reason"</span>]
          {"\n"}rec[<span className="s">"recovery_request"</span>]
          {"\n"}rec[<span className="s">"record_hash"</span>]  <span className="c"># links to the previous record</span>
        </pre>
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Where it runs and how fast">
          <table>
            <thead>
              <tr>
                <th scope="col">Where it runs</th>
                <th scope="col">Observed time and sample count</th>
              </tr>
            </thead>
            <tbody>
              {lat.map((r) => (
                <tr key={r.result}>
                  <td>{label(r)}</td>
                  <td>
                    {r.number}
                    {timingProtocol(r.result) && <span className="verdict-note">{timingProtocol(r.result)}</span>}
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
      <p>These timings describe the cited runs and hardware, not a service guarantee or a matched performance comparison. The ZeroGPU runs used the owner’s token; queueing and latency can differ for another user.</p>
      <p><code>analyze()</code> returns a single-image record; its growth-trend and passage-forecast fields are currently empty. Flask replays are a separate demonstration. The caller must also handle analysis exceptions, which can occur before a record is written.</p>
      <p>Implementation: <Src>culture/pipeline.py</Src> · host responsibilities: <Src>docs/host_platform.md</Src> · <a href="/#pilot">offline evaluation and commercial-use gates</a>.</p>
    </Section>
  );
}

/* ── release notes ── */

/* One release note: what changed, in a sentence or two; the numbers behind it, when they run long, under
   "Details". A qualifier on a number (n, "not fully blind", "simulated") stays with that number. */
function Note({ title, children, src, was, prev = "v0.2", more }) {
  return (
    <li className="note">
      <p>
        <b>{title}</b> {children}
      </p>
      {more ? (
        <details className="more-details">
          <summary>Details</summary>
          <p>{more}</p>
        </details>
      ) : null}
      {was ? <p className="note-was">In {prev}: {was}</p> : null}
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
  const cut = row(data, "Confluency error, EVICAN calibration profile");
  const prof = row(data, "Confluency error per imaging setup");
  const v05 = row(data, "Rules rules_v0.5 on held-out normal C2C12 frames");
  const qg = row(data, "Quality gate fail rate");
  const live = (data.examples.changes || []).map((c) => c.after.id);
  const cutMae = cut.number.match(/MAE ([\d.]+) → ([\d.]+) pp/).slice(1);
  const rev = row(data, "Sent to human review, held-out frames: boundary ambiguity");
  const amb = row(data, "Boundary ambiguity vs the reading's error");
  const fc = row(data, "Passage forecast");
  const spc = row(data, "SPC");
  const flagRate = row(data, "Anomaly flag rate, held-out normal");
  const zg = row(data, "Live latency, console Space on ZeroGPU");
  const ceiling = data.examples.items[0].confluency.ambiguity_ceiling.toFixed(2);
  const nEvican = nums(err.number)[1];
  const dt = data.dense_test;
  const dn = dt ? dt.points.length : 0;
  return (
    <>
      <article className="release" id="v0-4" aria-labelledby="v0-4-h">
        <header className="release-head">
          <h2 id="v0-4-h">v0.4</h2>
          <p>
            Local source at this site build: <code>{data.meta.rules}</code>
            <br />
            Records schema <code>{data.meta.schema}</code>; remote release unverified
          </p>
        </header>
        <div className="release-body">
          <section aria-labelledby="new4-h">
            <h3 id="new4-h">New</h3>
            <ul className="notes">
              <Note title="Confluency calibrated per imaging setup." src={prof.source} more={<>Method and pass criteria were committed before scoring: {prof.number}.</>}>
                Each microscope gets a cutoff fitted on its own labelled images and a 90% error band measured on images left out of the fit. Live for {live.join(" and ")}, each through a change record the repository owner approved, at the start of the stored chain.
              </Note>
              <Note title="Passage reads the error band." src="culture/rules.py" more={<>On held-out C2C12, which has no calibration: {v05.number}.</>}>
                A reading whose band clears the target passages; a band that includes the target goes to a person; a microscope with no calibration never passages on its reading alone. An anomaly flag still holds a passage.
              </Note>
              <Note title="Re-image is an action." src={qg.source}>
                An image that fails the quality gate calibrated for its microscope is sent back to be taken again before any reading is used. Fail rates on C2C12: {qg.number}.
              </Note>
              <Note title="Reviews and changes are their own records." src="culture/schema.json · docs/audit_mapping.md">
                A person’s review is a new record linked to the reading’s hash, so the reading is never edited. A profile change records the profile before and after by SHA-256, its evidence and who approved it.
              </Note>
              {dt ? (
                <Note
                  title="The passage range, tested on a lab no model had seen."
                  src={dt.sources.join(" · ")}
                  more={<>Within 5 pp of the experts: {dt.both.within5.F} of {dn} images fine-tuned, against {dt.both.within5.C} shipped. <a href="/validation#dense">The full test</a>.</>}
                >
                  {dn} hand-outlined images, with split, method and pass marks committed before any image was read. The shipped method read {dt.both.C.B1_mae.toFixed(2)} pp off on average and sent {dt.both.C.B4_review} of the {dt.both.C.n_60_100} images at 60% or more to a person; fine-tuned on the lab’s own images, the same model read {dt.both.F.B1_mae.toFixed(2)} pp off. Evidence, not a product change: the fine-tuned model does not decide.
                </Note>
              ) : null}
              <Note
                title="A fine-tuned reading beside the shipped one, for four test images."
                src="demo/lab_demo.py · configs/finetuned_models.yaml"
                more="Any other image, including a changed copy of one of the four, gets none. The weights inherit Cellpose-SAM’s non-commercial terms and are not published."
              >
                In the live console, four of that lab’s test images get a second reading from a retrain of the fine-tuned model, beside the shipped reading. It is marked not validated and decides nothing.
              </Note>
              <Note
                title="Model weights are checked before every reading."
                src="culture/approvals.py · configs/approved_changes.jsonl"
                more={
                  <>
                    The approvals log is hash-chained too. A weight mismatch gives no reading, and the record says why. For the shipped segmentation model and fine-tuned model, the local check compares weights with the latest effective model approval appended by inference time; a future-dated approval does not authorize them. This check does not authenticate who approved them; the host platform owns identity and signatures. Profile and rules activation is also host-managed: local copies are recorded, not locally enforced or authenticated. Records schema {data.meta.schema} carries the model check (<code>model_check</code>, <code>finetuned_reading</code>); the stored example chain on the records page was written under {JSON.parse(data.examples.items[0].record.canonical).schema_version}, before the check.
                  </>
                }
              >
                Before either checked segmentation model reads an image, its weights are compared with the latest effective approval for that model at inference time. A future-dated approval does not authorize a weight change. If the shipped model’s weights don’t match, there is no reading and no record.
              </Note>
            </ul>
          </section>

          <section aria-labelledby="changed4-h">
            <h3 id="changed4-h">Changed</h3>
            <ul className="notes">
              <Note
                title="Boundary ambiguity no longer decides."
                src={`${amb.source} · ${rev.source}`}
                prev="v0.3"
                was={`frames above ${ceiling} went to a person: ${rev.number}.`}
                more={<>The score {amb.number}.</>}
              >
                It tracks density, not the reading’s error, and stays in the record.
              </Note>
              <Note title="The EVICAN examples are read with their setup’s profile." src={cut.source} prev="v0.3" was="Cellpose’s default cutoff, with the calibrated cutoff shown beside it as validated, not yet released.">
                {cut.number}. {data.cutoff_disclosure}
              </Note>
            </ul>
          </section>

          <section aria-labelledby="uncal4-h">
            <h3 id="uncal4-h">Left uncalibrated</h3>
            <ul className="notes">
              <Note title="The C2C12 microscope of the examples and replays." src="configs/confluency_profiles.yaml">
                It has no labelled images, so its readings use Cellpose’s default cutoff with no band, and a passage at the target goes to a person. Its quality gate still runs.
              </Note>
            </ul>
          </section>
        </div>
      </article>

      <article className="release" id="v0-3" aria-labelledby="v0-3-h">
        <header className="release-head">
          <h2 id="v0-3-h">v0.3</h2>
          <p>
            Rules <code>rules_v0.4</code>
            <br />
            Branch <code>{data.meta.branch}</code>
          </p>
        </header>
        <div className="release-body">
          <details className="release-fold">
            <summary>
              <span>Per-image anomaly check, quality gate, flask history and forecast, records verifiable in the browser, checks V1–V10 and the live console; every headline number re-measured on real images.</span>
              <span className="release-fold-act">Show the notes</span>
            </summary>
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
            <h3 id="next-h">Validated, not released in v0.3</h3>
            <ul className="notes">
              <Note title="A recalibrated cell cutoff for the low reading." src={cut.source}>
                With the cutoff recalibrated on other images, the error on the same {nEvican} images drops from {cutMae[0]} to {cutMae[1]} pp ({cutMae[0]} pp is this study’s own run at the default cutoff; the first run, above, gave {nums(err.number)[0].toFixed(2)}). {data.cutoff_disclosure} It moved the review trigger and the anomaly bins, so it was held. Released in v0.4, above, as the EVICAN calibration profile.
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
          </details>
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
