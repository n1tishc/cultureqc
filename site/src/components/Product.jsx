import { AnomalyLayer } from "./Stage";
import { ProfileErrorFigure } from "./Profiles";
import { row } from "./Sections";
import { Action, Fig, Icon, Path, actionGloss, short } from "./ui";

/* The home page's product sections. Like the rest of the site, every number
   is read from data.json; the copy around it says what it is and where it
   came from. */

const ACTIONS = ["passage", "feed", "continue", "human_review", "reimage"];

const nums = (s) => (s.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);

function Step({ n, title, children, art }) {
  return (
    <li className="step">
      <div className="step-art">{art}</div>
      <div className="step-text">
        <h3>
          <span className="step-n num" aria-hidden="true">
            {n}
          </span>
          {title}
        </h3>
        {children}
      </div>
    </li>
  );
}

function MiniFrame({ ex, prob }) {
  const mask = { WebkitMaskImage: `url(${ex.prob})`, maskImage: `url(${ex.prob})` };
  return (
    <div className="mini frame" style={{ aspectRatio: `${ex.width} / ${ex.height}` }} data-prob={prob ? "" : undefined}>
      <img src={ex.image} width={ex.width} height={ex.height} alt="" loading="lazy" />
      {prob ? <div className="layer layer-prob" style={mask} /> : null}
    </div>
  );
}

/* The anomaly check reads the centre tile: crop the frame to it with the
   SVG's viewBox and draw the same patch distances the stage draws. */
function MiniTile({ ex }) {
  const t = ex.anomaly.tile;
  return (
    <div className="mini frame mini-tile" data-anom="">
      <svg viewBox={`${t.x} ${t.y} ${t.size} ${t.size}`} aria-hidden="true">
        <image href={ex.image} x="0" y="0" width={ex.width} height={ex.height} preserveAspectRatio="none" />
        <AnomalyLayer ex={ex} nested />
      </svg>
    </div>
  );
}

function MiniChain({ examples, ex }) {
  const byId = Object.fromEntries([...examples.items, ...(examples.changes || [])].map((e) => [e.id, e]));
  const order = examples.chain_order.map((id) => byId[id]);
  const i = ex.record.index - 1;
  const rows = order.slice(Math.max(0, i - 1), i + 2);
  return (
    <ol className="mini mini-chain" aria-hidden="true">
      {rows.map((e) => (
        <li key={e.id} data-this={e.id === ex.id ? "" : undefined}>
          <span className="num">#{e.record.index}</span>
          <code>{short(e.record.record_hash, 8)}</code>
        </li>
      ))}
    </ol>
  );
}

function MiniActions({ a }) {
  return (
    <ul className="mini mini-actions" aria-hidden="true">
      {ACTIONS.map((k) => (
        <li key={k} data-on={k === a ? "" : undefined}>
          <Action a={k} />
        </li>
      ))}
    </ul>
  );
}

export function HowItWorks({ data }) {
  const ex = data.examples.items.find((e) => e.id === "c2c12_normal_40_100") || data.examples.items[0];
  const c = ex.confluency;
  const a = ex.anomaly;
  return (
    <section className="sec" id="how" aria-labelledby="how-h">
      <div className="wrap">
        <header className="sec-head">
          <h2 id="how-h">One image in. A reading, a check, an action and a record out.</h2>
          <div>
            <p>
              <code>analyze()</code> runs once per flask visit. Below, its stored output for one held-out C2C12 frame, step by step: the densest normal frame among the examples, still below the passage target, so the culture continues.
            </p>
          </div>
        </header>
        <ol className="steps">
          <Step n="1" title="Image" art={<MiniFrame ex={ex} />}>
            <p>
              One phase-contrast frame per visit. This one is {ex.width} × {ex.height} px at {ex.um_per_px} µm/px.
            </p>
          </Step>
          <Step n="2" title="Confluency" art={<MiniFrame ex={ex} prob />}>
            <p>
              Cellpose-SAM’s cell-probability map, in cyan.{" "}
              {c.interval ? (
                <>
                  <b className="num">{c.pct.toFixed(1)}%</b> of pixels sit above the cutoff of this microscope’s calibration profile, with a 90% error band of <b className="num">{c.interval[0].toFixed(1)}–{c.interval[1].toFixed(1)}%</b> measured on held-out labelled images. If the band includes the passage target, a person decides.
                </>
              ) : (
                <>
                  <b className="num">{c.pct.toFixed(1)}%</b> of pixels sit above Cellpose-SAM’s default cutoff. This microscope has no labelled images, so it has no calibration profile: the reading has no error band, and a passage goes to a person.
                </>
              )}
            </p>
          </Step>
          <Step n="3" title="Anomaly check" art={<MiniTile ex={ex} />}>
            <p>
              DINOv2 patch features of the centre tile, against healthy frames of the same density. Score <b className="num">{a.score.toFixed(3)}</b>, threshold {a.threshold.toFixed(3)}: {a.flag ? "flagged" : "not flagged"}.
            </p>
          </Step>
          <Step n="4" title="Action" art={<MiniActions a={ex.action} />}>
            <p>
              {ex.rules} turns the reading, its error band, the quality gate and the flag into one action: here, {actionGloss(ex.action)}. A passage goes to a person when the band includes the target, when the microscope has no calibration, or when the anomaly check flags the frame; an image that fails the quality gate is taken again.
            </p>
          </Step>
          <Step n="5" title="Record" art={<MiniChain examples={data.examples} ex={ex} />}>
            <p>Appended to a hash-chained log with the image, map and config hashes and the model versions. Each hash covers the one before it.</p>
          </Step>
        </ol>
      </div>
    </section>
  );
}

/* What rules_v0.5 does with every held-out normal C2C12 frame (results/review_rate_v05.csv,
   from cached readings and quality metrics, no model run), one stacked bar per target. */
function RulesFigure({ data, letter = "B" }) {
  const rows = data.review_rate_v05.filter((r) => r.group === "C2C12 held-out, normal");
  const seq = data.review_rate.find((r) => r.group === "C2C12 held-out, full frames").sequences;
  const n = rows[0].n;
  const parts = (r) => [
    ["Re-image", r.reimage, "var(--reimage)"],
    ["Human review", r.review, "var(--review)"],
    ["Passage", r.passage, "var(--passage)"],
    ["Continue or feed", r.n - r.reimage - r.review - r.passage, "var(--rule-2)"],
  ];
  const pct = (k) => `${((100 * k) / n).toFixed(1)}%`;
  return (
    <Fig
      letter={letter}
      title={`What ${rows[0].rules} does with held-out frames`}
      legend={
        <>
          All {n} held-out normal C2C12 frames ({seq} sequences), from the compute cache’s readings; no model run. This microscope has no labelled images, so it has no calibration profile: a reading at or above the target goes to a person, and none reaches 80%. Its quality gate runs first and asks for a new image on {rows[0].reimage} ({pct(rows[0].reimage)}). Source: <Path>results/review_rate.md</Path>.
        </>
      }
    >
      <div className="rules-fig">
        {rows.map((r) => (
          <div className="rules-row" key={r.target}>
            <div className="rules-head">
              <span>{r.target.toFixed(0)}% target</span>
              <span className="v">
                re-image {r.reimage} · review {r.review}
              </span>
            </div>
            <div className="rules-track" role="img" aria-label={`${r.target.toFixed(0)}% target: ` + parts(r).map(([k, v]) => `${k} ${v}`).join(", ")}>
              {parts(r).reduce(
                (acc, [k, v, c]) => {
                  acc.out.push(<i key={k} style={{ left: `${(100 * acc.x) / n}%`, width: `${(100 * v) / n}%`, background: c }} />);
                  acc.x += v;
                  return acc;
                },
                { x: 0, out: [] },
              ).out}
            </div>
          </div>
        ))}
        <ul className="rules-key">
          {parts(rows[0]).map(([k, , c]) => (
            <li key={k}>
              <i style={{ background: c }} />
              {k}
            </li>
          ))}
        </ul>
      </div>
    </Fig>
  );
}

export function Accuracy({ data }) {
  const P = data.profiles;
  const msc = P.items.find((p) => p.id === "msc_phase");
  const ev = P.items.find((p) => p.id === "evican_mixed");
  return (
    <section className="sec" id="accuracy" aria-labelledby="accuracy-h">
      <div className="wrap feature">
        <div className="feature-text">
          <h2 id="accuracy-h">A confluency reading you can check against experts</h2>
          <p>
            Confluency comes from Cellpose-SAM’s probability map, counted above a cutoff calibrated for each microscope on labelled images from it. On held-out images the calibrated cutoff brings the error against expert masks from {msc.shipped.mae.toFixed(2)} to <b className="num">{msc.profile.mae.toFixed(2)} pp</b> on mesenchymal stem cells ({msc.n_test} images), and from {ev.shipped.mae.toFixed(2)} to {ev.profile.mae.toFixed(2)} pp on EVICAN’s mixed microscopes ({ev.n_test} images; not fully blind, as the validation page explains).
          </p>
          <p>
            Every reading carries the 90% error band measured on images left out of the fit: ±{msc.band_pp.toFixed(1)} pp for the stem-cell microscope, ±{ev.band_pp.toFixed(1)} pp across EVICAN’s mixed ones. A passage needs the whole band above the target. When the band includes the target, or the microscope has no calibration yet, a person decides.
          </p>
          <a className="more" href="/validation#profiles">
            How each setup was calibrated <Icon name="passage" />
          </a>
        </div>
        <div className="figs feature-figs">
          <ProfileErrorFigure data={data} />
          <RulesFigure data={data} />
        </div>
      </div>
    </section>
  );
}

/* A datasheet: what was measured, the result with its n, and the file it
   came from. The last row is computed in this browser. */
export function Specs({ data, verify }) {
  const ex = data.examples;
  const okCount = verify ? verify.filter((v) => v.ok).length : null;
  const before = row(data, "Confluency error, Cellpose-SAM");
  const rescored = row(data, "Confluency error, EVICAN calibration profile").number.match(/MAE ([\d.]+) →/)[1];
  const [n33] = nums(before.number).slice(1, 2);
  const flags = row(data, "Anomaly flag rate, held-out normal");
  const flagPct = nums(flags.number)[0];
  // Each row: label, results row, and an optional note that says what the number means.
  const spec = [
    ["Confluency error against expert masks, at Cellpose’s default cutoff", before,
      `Before any calibration. The calibration study scored the same ${n33} images again in a separate run and got ${rescored} pp; the row below starts from that run.`],
    ["Confluency error with each setup’s calibration", row(data, "Confluency error per imaging setup")],
    ["What the rules do with held-out C2C12 frames", row(data, "Rules rules_v0.5 on held-out normal C2C12 frames")],
    ["Anomaly flags on healthy held-out frames", flags,
      `About 1 healthy frame in ${Math.round(100 / flagPct)} is flagged. A flag changes only a passage call, which then goes to a person; continue and feed are unchanged.`],
    ["One analysis on the live console (ZeroGPU), first run after a restart", row(data, "Live latency, console Space on ZeroGPU, first run")],
    ["The same, second run", row(data, "Live latency, console Space on ZeroGPU, second run")],
  ];
  return (
    <section className="sec" id="specs" aria-labelledby="specs-h">
      <div className="wrap">
        <header className="sec-head">
          <h2 id="specs-h">Measured on real, held-out images</h2>
          <div>
            <p>Every figure on this site comes from the repository’s stored output, with its n and its source file. The validation page has the full set, including the checks that failed and what they changed.</p>
          </div>
        </header>
        <div className="spec" role="table" aria-label="Measured performance">
          {spec.map(([label, r, note]) => (
            <div className="spec-row" role="row" key={label}>
              <div role="rowheader">{label}</div>
              <div role="cell" className="spec-v">
                {r.number}
                {note ? <span className="spec-note">{note}</span> : null}
              </div>
              <div role="cell" className="spec-src">
                <Path>{r.source}</Path>
              </div>
            </div>
          ))}
          <div className="spec-row" role="row">
            <div role="rowheader">Records re-hashed in your browser</div>
            <div role="cell" className="spec-v" aria-live="polite">
              {verify ? `${okCount} of ${verify.length} match their stored SHA-256 and link to the record before` : "re-hashing…"}
            </div>
            <div role="cell" className="spec-src">
              <Path>site/src/lib/verify.js</Path>
            </div>
          </div>
        </div>
        <p className="spec-foot">
          <a className="more" href="/validation">
            All {data.validation.length} checks, V1–V{data.validation.length} <Icon name="passage" />
          </a>
          <span>
            {ex.items.length} stored examples · {data.replays.length} held-out flask replays · rules {data.meta.rules.replace("rules_", "")}
          </span>
        </p>
      </div>
    </section>
  );
}

function detectKind(text) {
  const t = text.toLowerCase();
  if (t.startsWith("yes")) return ["pass", "Yes"];
  if (t.startsWith("not tested")) return ["untested", "Not tested"];
  if (t.startsWith("not reliably")) return ["mixed", "Not reliably"];
  return ["fail", "No"];
}

/* "Image quality (blur / exposure / uneven illumination)" → name, and the
   faults it covers as a phrase. */
function splitIssue(issue) {
  const m = issue.match(/^(.*?)\s*\((.*)\)$/);
  if (!m) return [issue, ""];
  const parts = m[2].split(" / ");
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} or ${parts[parts.length - 1]}` : parts[0];
  return [m[1], list];
}

/* What the pipeline reads from an image, beside what the matrix leaves to
   another test. The verdict for each row, with its evidence, is on the
   validation page. */
export function Scope({ data }) {
  const rows = data.detectability.rows;
  const gated = rows.filter((r) => detectKind(r.detectable_here)[0] === "pass");
  const elsewhere = rows.filter((r) => detectKind(r.detectable_here)[0] !== "pass");
  return (
    <section className="sec" id="scope" aria-labelledby="scope-h">
      <div className="wrap">
        <header className="sec-head">
          <h2 id="scope-h">Built for confluency QC, clear about the rest</h2>
          <div>
            <p>cultureQC reads confluency, gates image quality and flags unusual frames for a person. It is not a contamination test: with simulated bacteria at their real size, the anomaly flag is at chance on the tested setup. Everything else is listed with the test to confirm it with.</p>
          </div>
        </header>
        <div className="scope-split">
          <div className="scope-col">
            <h3>What it reads</h3>
            <ul className="scope-in">
              <li>
                <Icon name="check" />
                <div>
                  <b>Confluency</b>
                  <span>Cellpose-SAM’s reading at the cutoff calibrated for the microscope, with a measured 90% error band. When the band includes the passage target, or the microscope has no calibration, a person decides.</span>
                </div>
              </li>
              {gated.map((r) => {
                const [name, faults] = splitIssue(r.issue);
                return (
                  <li key={r.issue}>
                    <Icon name="check" />
                    <div>
                      <b>{name}</b>
                      <span>{faults ? `Where a gate is calibrated for the microscope (here, C2C12), it fails frames for ${faults}, and the action is ${r.confirm_with.toLowerCase()}.` : r.detectable_here}</span>
                    </div>
                  </li>
                );
              })}
              <li>
                <Icon name="check" />
                <div>
                  <b>Unusual frames</b>
                  <span>An anomaly score for the frame’s {data.examples.items[0].anomaly.tile.size} px centre tile, against healthy frames of the same density. A flag holds a passage for a person; it does not name a cause.</span>
                </div>
              </li>
            </ul>
          </div>
          <div className="scope-col">
            <h3>Confirm with a separate test</h3>
            <dl className="scope-out">
              {elsewhere.map((r) => (
                <div key={r.issue}>
                  <dt>{r.issue}</dt>
                  <dd>{r.confirm_with}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
        <p className="spec-foot">
          <a className="more" href="/validation#detectability">
            What was tested for each, and the result <Icon name="passage" />
          </a>
          <span>
            Source: <Path>configs/detectability.yaml</Path>, hashed into every record
          </span>
        </p>
      </div>
    </section>
  );
}
