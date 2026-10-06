import { Fig, Path, Section, Verdict } from "./ui";

/* The passage-range test on a dense dataset no model had seen (results/confluency_mcellseg.md, sealed,
   scored once; results/confluency_mcellseg_swap.md, its pre-registered replication with the halves
   swapped, scored once). Every number comes from data.dense_test, which build_data.py copies from those
   results files. Not in the product: the fine-tuned weights are a measurement. */

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

function Scatter({ d, arm, letter, title }) {
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
    <li className="note">
      <p>
        <b>{title}</b> {children}
      </p>
    </li>
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
            The MSC and EVICAN profiles above could not measure the passage range: their test images held almost no flasks at 60–90%. This test can. {d.dataset}: {n} images from {d.setups} microscope setups, every cell outlined by hand, published after Cellpose-SAM and not in its training data. It compares the shipped method, a calibration profile per setup, with the same model fine-tuned on the lab’s own labelled images and then calibrated. The split, the method and the pass marks were committed before any image was read, and each half of the data was scored once: first as a sealed test, then with the halves swapped.
          </p>
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
      <h3 className="sub-h">Against the criteria committed before scoring</h3>
      <CriteriaTable d={d} />
      <h3 className="sub-h">What it shows, and what it does not</h3>
      <ul className="notes">
        <Note title="The shipped method fails safe, but rarely decides.">
          Over both halves it called no ready flask continue, and it sent {b.C.B4_review} of the {b.C.n_60_100} images at 60% or more to a person. Its average error at 60–90% was {fx(b.C.B2_mae)} pp.
        </Note>
        <Note title="Fine-tuning reads closer, in both halves.">
          Average error {fx(b.F.B1_mae)} pp against {fx(b.C.B1_mae)} on all {n} images; {b.within5.F} read within 5 pp of the experts, against {b.within5.C}. In the sealed test the comparison fixed in advance held. With the halves swapped the difference was about the same size ({sgn(d.swapped.contrast.diff)} pp), but its interval includes zero, so by its own rule it is not a replication.
        </Note>
        <Note title="It does not yet decide passage on its own.">
          Over both halves {b.F.B4_agree} of its {b.F.B4_decided} decided calls agreed with the experts, short of the {d.limits.agree * 100}% mark: passage calls on flasks at {b.wrong.F.map((x) => `${fx(x, 1)}%`).join(" and ")}. It still sends {pct(b.F.review_share)} of images to a person, and the rule that sends a reading to a person when its band includes the target stays.
        </Note>
        <Note title="Not in the product.">
          A fine-tuned profile would be a model of the lab’s own, trained on {d.sealed.n_train}–{d.swapped.n_train} images with every cell outlined, recorded as a change with its weights’ SHA-256, and checked on held-out images before use. Here the fine-tuned weights are a measurement; they inherit Cellpose-SAM’s non-commercial terms.
        </Note>
        <Note title="Why MSC still reads “Validated” above.">
          That status covers the criteria its test images could measure; the passage-range ones (A2–A4) were not measurable on MSC or EVICAN. This is the first held-out measurement of them, and its limits are its own: {d.scope}, and {b.C.n_ge_T} images at or above {d.limits.target}%.
        </Note>
      </ul>
    </Section>
  );
}
