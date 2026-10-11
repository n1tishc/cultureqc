import { useState } from "react";
import { Fig, Icon, Path, Section, Verdict } from "./ui";

/* The passage-range test on a dense dataset no model had seen (results/confluency_mcellseg.md, sealed,
   scored once; results/confluency_mcellseg_swap.md, its pre-registered replication with the halves
   swapped, scored once). Every number comes from data.dense_test, which build_data.py copies from those
   results files. The fine-tuned model reads four of this lab's test images in the live console, beside the
   shipped reading, and decides nothing (demo/lab_demo.py). */

const fx = (x, d = 2) => Number(x).toFixed(d);
const sgn = (x, d = 2) => (x >= 0 ? `+${fx(x, d)}` : `−${fx(Math.abs(x), d)}`);
const ci = (c) => `${sgn(c[0])} to ${sgn(c[1])}`;
const ARMS = [
  ["C", "Shipped"],
  ["F", "Fine-tuned"],
];
const HALVES = [
  ["sealed", "Sealed test"],
  ["swapped", "Halves swapped"],
  ["both", "Both halves"],
];

export function Scatter({ d, arm, letter, title }) {
  const pts = d.points;
  const n = pts.length;
  const w5 = d.both.within5[arm];
  const mae = d.both[arm].B1_mae;
  const T = d.limits.target;
  const W = 300;
  const H = 300;
  const m = { l: 34, r: 10, t: 10, b: 30 };
  const X = (v) => m.l + (v / 100) * (W - m.l - m.r);
  const Y = (v) => H - m.b - (v / 100) * (H - m.t - m.b);
  const ticks = [0, 20, 40, 60, 80, 100];
  const band = `M${X(0)},${Y(5)} L${X(95)},${Y(100)} L${X(100)},${Y(100)} L${X(100)},${Y(95)} L${X(5)},${Y(0)} L${X(0)},${Y(0)} Z`;
  const ink = arm === "F" ? "var(--cell-ink)" : "var(--ink-3)";
  return (
    <Fig
      letter={letter}
      title={title}
      legend={
        <>
          {n} images, each read by models that never trained on it. Average error {fx(mae)} pp; {w5} of {n} within 5 pp of the experts (pale strip). Shaded: 60–90%. Dashed: the {T}% passage target.
        </>
      }
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", maxWidth: 440, height: "auto", display: "block", margin: "0 auto" }}
        role="img"
        aria-label={`${title}: ${w5} of ${n} readings within 5 percentage points of the experts, average error ${fx(mae)} points`}
      >
        <rect x={X(60)} y={Y(100)} width={X(90) - X(60)} height={Y(0) - Y(100)} fill="var(--hold-l)" opacity="0.14" />
        <path d={band} fill={ink} opacity="0.09" />
        {ticks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={W - m.r} y1={Y(t)} y2={Y(t)} stroke="var(--rule)" />
            <text x={m.l - 6} y={Y(t) + 3.5} textAnchor="end" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-3)">
              {t}
            </text>
            <text x={X(t)} y={H - m.b + 14} textAnchor="middle" fontSize="10.5" fontFamily="var(--mono)" fill="var(--ink-3)">
              {t}
            </text>
          </g>
        ))}
        <line x1={X(0)} y1={Y(0)} x2={X(100)} y2={Y(100)} stroke="var(--ink-2)" strokeWidth="1" />
        <line x1={X(0)} y1={Y(T)} x2={X(100)} y2={Y(T)} stroke="var(--ink-2)" strokeWidth="1" strokeDasharray="4 3" />
        {pts.map((p, i) => (
          <circle key={i} cx={X(p.gt)} cy={Y(Math.min(100, Math.max(0, p[arm])))} r="2.6" fill={ink} fillOpacity="0.72" />
        ))}
        <text x={X(50)} y={H - 2} textAnchor="middle" fontSize="10.5" fill="var(--ink-2)">
          experts’ confluency (%)
        </text>
        <text x={10} y={Y(50)} textAnchor="middle" fontSize="10.5" fill="var(--ink-2)" transform={`rotate(-90 10 ${Y(50)})`}>
          reading (%)
        </text>
      </svg>
    </Fig>
  );
}

const kind = (v) => (v === "pass" ? "pass" : v === "fail" ? "fail" : "none");

function CriteriaTable({ d }) {
  const L = d.limits;
  const rows = [
    [`Average error, all images (≤ ${L.mae} pp)`, (c) => <V v={c.verdicts.B1}>{fx(c.B1_mae)} pp</V>],
    [`Average error at 60–90% (≤ ${L.mae} pp)`, (c) => <V v={c.verdicts.B2}>{fx(c.B2_mae)} pp</V>],
    [`Mean signed error at 60–90% (within ±${L.bias} pp)`, (c) => <V v={c.verdicts.B3}>{sgn(c.B3_bias)} pp</V>],
    [`Calls at ${L.target}% on images at 60% or more: passage / continue / to a person`,
      (c) => `${c.B4_passage} / ${c.B4_continue} / ${c.B4_review}`],
    [`Decided calls that agree with the experts (≥ ${L.agree * 100}%)`, (c) => <V v={c.verdicts.B4}>{c.B4_agree} of {c.B4_decided}</V>],
    [`Ready flasks (≥ ${L.target}%) called continue`, (c) => String(c.B4_ready_called_continue)],
    [`Within the error band, all images (≥ ${L.cover * 100}%)`, (c) => <V v={c.verdicts.B5}>{c.B5_covered} of {c.B5_n}</V>],
    ["Images sent to a person", (c) => `${fx(c.review_share * 100, 1)}%`],
  ];
  const primary = (h) =>
    d[h].contrast.ci[0] > 0 ? ["pass", "comparison fixed in advance: held"] : ["fail", "comparison fixed in advance: interval includes zero"];
  const bar = { sealed: primary("sealed"), swapped: primary("swapped"), both: ["none", "secondary view, fixed in advance"] };
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Pre-registered criteria for the shipped and fine-tuned readings">
      <table>
        <thead>
          <tr>
            <th scope="col" rowSpan={2}>Criterion (pass mark)</th>
            {HALVES.map(([h, label]) => (
              <th scope="colgroup" colSpan={2} key={h}>
                {label}
                <span className="verdict-note">
                  {d[h].C.n} images · {d[h].C.n_60_90} at 60–90% · {d[h].C.n_ge_T} at ≥ {L.target}%
                </span>
              </th>
            ))}
          </tr>
          <tr>
            {HALVES.flatMap(([h]) => ARMS.map(([a, label]) => (
              <th scope="col" key={h + a}>
                {label}
              </th>
            )))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, cell]) => (
            <tr key={label}>
              <td>{label}</td>
              {HALVES.flatMap(([h]) => ARMS.map(([a]) => (
                <td key={h + a} className="num">
                  {cell(d[h][a])}
                </td>
              )))}
            </tr>
          ))}
          <tr>
            <td>Fine-tuned closer at 60–90%: shipped minus fine-tuned error, 95% interval</td>
            {HALVES.map(([h]) => (
              <td key={h} colSpan={2} className="num">
                {sgn(d[h].contrast.diff)} pp ({ci(d[h].contrast.ci)})
                <span className="verdict-note">
                  <Verdict k={bar[h][0]}>{bar[h][1]}</Verdict>
                </span>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function V({ v, children }) {
  return (
    <>
      {children}
      <span className="verdict-note">
        <Verdict k={kind(v)}>{v}</Verdict>
      </span>
    </>
  );
}

function Note({ title, children }) {
  return (
    <li className="card-note">
      <h4>{title.replace(/\.$/, "")}</h4>
      <p>{children}</p>
    </li>
  );
}

/* What the two readings cover on one test image per setup (results/confluency_finetune_figure.md): the shipped
   method's calibration profile beside the fine-tuned model, each with the experts' outline. The panels are cut from
   the committed figure by build_data.py; the readings are the scored test's. */
export function FineTuneFigure({ data, letter = "C" }) {
  const f = data.finetune_figure;
  const [i, setI] = useState(0);
  if (!f) return null;
  const p = f.panels[i];
  const arms = [
    ["C", "Shipped method", "a calibration profile per setup"],
    ["F", "Fine-tuned", "on the lab’s own images, then calibrated"],
  ];
  return (
    <Fig
      letter={letter}
      title="What each reading counts, on one test image per setup"
      className="ft-fig"
      legend={
        <>
          Cyan: the pixels the reading counts. Yellow: the experts’ outline. One test image per setup, the one at 60–90% closest to 75%, by a rule fixed before drawing. Not a new result: the scored fine-tuned model was not kept, so the picture is drawn with <code>{f.model}</code>, a retrain on the same {f.n_train} images, each drawn reading within {f.tol.toFixed(1)} pp of the scored one; the readings given are the scored test’s. Images: mCellSeg, CC BY 4.0. Source: <Path>{f.source}</Path>.
        </>
      }
    >
      <div className="seg-tabs" role="tablist" aria-label="Imaging setup">
        {f.panels.map((q, k) => (
          <button key={q.setup} type="button" role="tab" aria-selected={k === i} onClick={() => setI(k)}>
            {q.setup}
          </button>
        ))}
      </div>
      <div className="ft-pair" role="tabpanel">
        {arms.map(([a, title, sub]) => {
          const off = p[a] - p.gt;
          return (
            <figure key={a}>
              <img src={p[`${a}_img`]} alt={`${title} reading of a ${p.setup} test image: ${p[a].toFixed(1)}% counted, against the experts’ ${p.gt.toFixed(1)}%.`} loading="lazy" />
              <figcaption>
                <span className="ft-title">
                  <b>{title}</b> {sub}
                </span>
                <span className="ft-nums num">
                  {p[a].toFixed(1)}% <span>vs experts {p.gt.toFixed(1)}%</span>
                  <em data-big={Math.abs(off) > 5 ? "" : undefined}>{sgn(off, 1)} pp</em>
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>
    </Fig>
  );
}

/* The home page's short version: the two readings side by side, the shipped one first, and where the
   full test is. The fine-tuned model is evidence here, as on the validation page; it decides nothing. */
export function PassageRange({ data }) {
  const d = data.dense_test;
  if (!d) return null;
  const n = d.points.length;
  const b = d.both;
  return (
    <Section
      id="passage"
      title="In the passage range, on a lab no model had seen"
      lede={
        <>
          <p>
            {n} hand-outlined images from a public dataset, published after Cellpose-SAM. The shipped method fails safe: it sent {b.C.B4_review} of the {b.C.n_60_100} images at 60% or more to a person and called no ready flask continue. Fine-tuned on the lab’s own images, the same model read within 5 pp of the experts on {b.within5.F} of {n}, against {b.within5.C}.
          </p>
          <p>That is evidence for a lab training its own model, not a product change: the fine-tuned reading decides nothing.</p>
          <p>
            <a className="more" href="/validation#dense">
              The full test, with the pass marks committed before scoring <Icon name="passage" />
            </a>
          </p>
        </>
      }
    >
      <div className="figs g2">
        <Scatter d={d} arm="C" letter="A" title="Shipped method: a calibration profile per setup" />
        <Scatter d={d} arm="F" letter="B" title="Fine-tuned on the lab’s own images, then calibrated" />
      </div>
    </Section>
  );
}

export function DenseTest({ data }) {
  const d = data.dense_test;
  if (!d) return null;
  const n = d.points.length;
  const b = d.both;
  const pct = (x) => `${fx(x * 100, 1)}%`;
  return (
    <Section
      id="dense"
      title="The passage range, on a lab it had never seen"
      lede={
        <>
          <p>
            The calibration tests above held almost no flasks at 60–90%, where passage is decided. This one does: {n} images from {d.setups} microscope setups of one lab, every cell outlined by hand, published after Cellpose-SAM. It compares the shipped method, a calibration profile per setup, with the same model fine-tuned on the lab’s own labelled images. Split, method and pass marks were committed before any image was read.
          </p>
          <details className="more-details">
            <summary>How the test was run</summary>
            <p>
              {d.dataset}. The images are not in Cellpose-SAM’s training data. Within each setup the images were split into a calibration half and a test half, spanning the same densities: the fine-tuned model was trained, and both methods calibrated, on the calibration half, and both were read on the test half. The sealed test was scored once. Swapping the halves was planned after that score and committed before its models were trained; what had already been seen is listed in its write-up, and it too was scored once.
            </p>
          </details>
          <p className="sources">
            <Path>{d.sources[0]}</Path> · <Path>{d.sources[1]}</Path>
          </p>
        </>
      }
    >
      <div className="figs g2">
        <Scatter d={d} arm="C" letter="A" title="Shipped method: a calibration profile per setup" />
        <Scatter d={d} arm="F" letter="B" title="Fine-tuned on the lab’s own images, then calibrated" />
      </div>
      <div className="figs" style={{ marginTop: 16 }}>
        <FineTuneFigure data={data} />
      </div>
      <h3 className="sub-h">Against the criteria committed before scoring</h3>
      <CriteriaTable d={d} />
      <h3 className="sub-h">What it shows, and what it does not</h3>
      <ul className="card-notes">
        <Note title="The shipped method fails safe, but rarely decides.">
          Over both halves it called no ready flask continue, and it sent {b.C.B4_review} of the {b.C.n_60_100} images at 60% or more to a person. Its average error at 60–90% was {fx(b.C.B2_mae)} pp.
        </Note>
        <Note title="Fine-tuning reads closer, in both halves.">
          Average error {fx(b.F.B1_mae)} pp against {fx(b.C.B1_mae)} on all {n} images; {b.within5.F} read within 5 pp of the experts, against {b.within5.C}. In the sealed test the comparison fixed in advance held. With the halves swapped the difference was about the same size ({sgn(d.swapped.contrast.diff)} pp), but its interval includes zero, so by its own rule it is not a replication.
        </Note>
        <Note title="It does not yet decide passage on its own.">
          Over both halves {b.F.B4_agree} of its {b.F.B4_decided} decided calls agreed with the experts, short of the {d.limits.agree * 100}% mark: passage calls on flasks at {b.wrong.F.map((x) => `${fx(x, 1)}%`).join(" and ")}. It still sends {pct(b.F.review_share)} of images to a person, and the rule that sends a reading to a person when its band includes the target stays.
        </Note>
        <Note title="In the live console, beside the shipped reading.">
          Four of this lab’s test images have buttons in the{" "}
          <a href={data.meta.console_url} target="_blank" rel="noreferrer">live console</a>, where a retrain of this fine-tuned model ({d.sealed.n_train} images, same recipe) reads them beside the shipped reading. It is marked not validated, decides nothing, and only those four exact files get it; its weights are checked against an approved change record before every reading. A fine-tuned model that decided would be the lab’s own, approved as a change and checked on held-out images first. The weights inherit Cellpose-SAM’s non-commercial terms and are not published.
        </Note>
        <Note title="Why MSC reads “Validated where measurable” above.">
          That status covers only the criteria its test images could measure; the passage-range ones (A2–A4) were not measurable on MSC or EVICAN.{" "}
          {d.msc_dense ? (
            <>
              Dense regions of the MSC images themselves read {fx(Math.abs(d.msc_dense.bias))} pp {d.msc_dense.bias < 0 ? "low" : "high"} on average at that profile’s cutoff, {d.msc_dense.over10} of {d.msc_dense.n} off by more than 10 pp, in a test that could not separate density from how the regions were picked (<Path>{d.msc_dense.source}</Path>).{" "}
            </>
          ) : null}
          This is the first held-out measurement of the passage range on whole images, and its limits are its own: {d.scope}, and {b.C.n_ge_T} images at or above {d.limits.target}%.
        </Note>
      </ul>
    </Section>
  );
}
