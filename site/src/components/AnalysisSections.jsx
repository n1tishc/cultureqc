import { useState } from "react";
import LadderCell from "./LadderCell";
import { MORPH } from "../lib/labels";

const LINES = ["A172", "BT474", "BV2", "Huh7"];
const SEVS = [
  ["clean", "Clean control"],
  ["early", "Early"],
  ["mid", "Mid"],
  ["late", "Late"],
];

export function MeasureTable({ leaves }) {
  return (
    <section className="sec" id="sec-measure2">
      <div className="sechead rv">
        <h2>Two methods, four real fields.</h2>
        <span className="docaddr">Confluency &middot; head to head</span>
      </div>
      <p className="tblcap rv">
        Run on this machine. Disagreement is the gap between the two methods on
        the same field, not a labelled error.
      </p>
      <p className="scrollnote rv">Table scrolls sideways &rarr;</p>
      <div
        className="scrollx rv"
        tabIndex={0}
        role="region"
        aria-label="Confluency method comparison, scrollable"
      >
        <table className="tbl">
          <thead>
            <tr>
              <th scope="col">Cell line</th>
              <th scope="col">cultureQC</th>
              <th scope="col">Threshold baseline</th>
              <th scope="col">Disagreement</th>
              <th scope="col">Morphology</th>
            </tr>
          </thead>
          <tbody id="mtbody">
            {LINES.map((id) => {
              const d = leaves.find((x) => x.id === id);
              const gap = Math.abs(d.confluency - d.baseline);
              return (
                <tr key={id}>
                  <td>{id}</td>
                  <td className="mono">{d.confluency.toFixed(2)}%</td>
                  <td className="mono">{d.baseline.toFixed(2)}%</td>
                  <td className={"mono gap" + (gap < 10 ? " small" : "")}>
                    {gap.toFixed(1)} pp
                  </td>
                  <td>{MORPH[id]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="foot rv">
        On rounded, high-contrast microglia the two nearly agree; on flat,
        low-contrast epithelial sheets the threshold sees almost no cells at all.
      </p>
    </section>
  );
}

export function Ladder({ ladder }) {
  const [boxes, setBoxes] = useState(false);
  const at = (line, sev) =>
    ladder.find((x) => x.line === line && x.sev === sev);

  return (
    <section className="sec" id="sec-ladder">
      <div className="sechead rv">
        <h2>The severity matrix.</h2>
        <span className="docaddr">QC classifier &middot; 16 tiles</span>
      </div>
      <p className="lede rv">
        Four real fields &times; four severities, passed through the shipped
        classifier. Four clean controls read normal; all twelve contaminated
        tiles were flagged at 1.000.
      </p>

      <p className="scrollnote rv">Matrix scrolls sideways &rarr;</p>
      <div
        className="ladwrap rv scrollx"
        id="ladwrap"
        data-boxes={boxes ? "on" : "off"}
        tabIndex={0}
        role="region"
        aria-label="Contamination severity matrix, scrollable"
      >
        <div className="ladgrid" id="ladgrid">
          <div></div>
          {SEVS.map(([k, label]) => {
            const rows = ladder.filter((x) => x.sev === k);
            const lo = Math.min(...rows.map((r) => r.n));
            const hi = Math.max(...rows.map((r) => r.n));
            return (
              <div className="ladhead" key={k}>
                {label}
                <b>
                  {k === "clean"
                    ? "0 organisms"
                    : (lo === hi ? lo : lo + "–" + hi) + " organisms"}
                </b>
              </div>
            );
          })}
          {LINES.map((line) => (
            <Row key={line} line={line} at={at} />
          ))}
        </div>
      </div>
      <div className="ladfoot rv">
        <label className="tog solo">
          <input
            type="checkbox"
            id="t-ladbox"
            checked={boxes}
            onChange={(e) => setBoxes(e.target.checked)}
          />
          <span className="dot" aria-hidden="true"></span>Grad-CAM evidence
        </label>
        <p className="note">
          Built from a library of 2,351 bacterial sprites at their source optical
          scale, larger than a real objective would show. See{" "}
          <a href="#sec-provenance">provenance</a>, below.
        </p>
      </div>
    </section>
  );
}

/* The grid is a flat CSS grid, so a row is a label followed by four cells
   rather than a wrapping element. */
function Row({ line, at }) {
  return (
    <>
      <div className="ladlab">{line}</div>
      {SEVS.map(([k]) => (
        <LadderCell key={k} cell={at(line, k)} line={line} sev={k} />
      ))}
    </>
  );
}

const DISCLOSURES = [
  [
    "QC classifier",
    "Trained entirely on synthetic data.",
    "EfficientNet-B0, trained on real phase-contrast microscopy with bacterial sprites and turbidity composited in, plus synthetic detachment and image artifacts. No real contaminated-culture training data exists for it, and the reported recall is measured on that synthetic distribution — not on clinical isolates.",
  ],
  [
    "Segmentation",
    "Cellpose-SAM, zero-shot, never fine-tuned per line.",
    "Used for the confluency probability map with no per-cell-line fine-tuning, which is exactly why the figure transfers across morphologies.",
  ],
  [
    "Evidence boxes",
    "Grad-CAM over the classifier's own activations.",
    "Thresholded into at most eight regions. They show where the model looked, not a second model's opinion of where contamination is.",
  ],
  [
    "A known limit",
    "The synthetic organisms are larger than a real objective would show.",
    "Sprites are composited at their source optical scale. Shrinking them below roughly half that size degrades the classifier, which is the honest boundary of what these numbers cover.",
  ],
];

export function Provenance() {
  return (
    <section className="sec" id="sec-provenance">
      <div className="sechead rv">
        <h2>What it is trained on, and what it is not.</h2>
        <span className="docaddr">Provenance</span>
      </div>
      <p className="lede rv">
        A QC model that can pause an automated line has to be honest about where
        its evidence comes from. Open any line for the detail.
      </p>
      <div className="discl rv">
        {DISCLOSURES.map(([key, claim, body]) => (
          <details className="dline" key={key}>
            <summary>
              <span className="dkey">{key}</span>
              <span className="dclaim">{claim}</span>
            </summary>
            <p>{body}</p>
          </details>
        ))}
        <details className="dline">
          <summary>
            <span className="dkey">This page</span>
            <span className="dclaim">
              Every number here came out of the shipped pipeline.
            </span>
          </summary>
          <p>
            Four real phase-contrast fields (A172, BT474, BV2, Huh7), one with
            contamination composited in at full resolution, and four 256&times;256
            challenge tiles. Every mask, box and hash was produced by the pipeline
            on the author&rsquo;s machine, not mocked up.
          </p>
        </details>
      </div>
    </section>
  );
}
