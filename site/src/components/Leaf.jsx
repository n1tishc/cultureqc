import { useEffect, useState } from "react";
import Plate from "./Plate";
import Counter from "./Counter";
import {
  ACTION_LABEL,
  ACTION_TONE,
  CLASSES,
  FLAGGED_LEAF,
  FLAG_LABEL,
  FLAG_SHORT,
  FLAG_TONE,
  pad2,
} from "../lib/labels";
import { RM } from "../lib/motion";

const ROWS = 5;

export default function Leaf({ leaves }) {
  const [idx, setIdx] = useState(FLAGGED_LEAF);
  const [run, setRun] = useState(0);
  /* The first paint is the destination, not a performance: someone arriving on
     this view should not watch an animation they did not ask for. */
  const [instant, setInstant] = useState(true);
  const [rowsIn, setRowsIn] = useState(() => Array(ROWS).fill(false));
  const [bars, setBars] = useState(false);
  const d = leaves[idx];

  useEffect(() => {
    const quick = RM.matches || instant;
    setRowsIn(Array(ROWS).fill(false));
    setBars(false);
    const timers = [];
    const at = (ms, fn) => timers.push(setTimeout(fn, quick ? 0 : ms));
    for (let k = 0; k < ROWS; k++)
      at(340 + k * 90, () =>
        setRowsIn((r) => {
          const n = r.slice();
          n[k] = true;
          return n;
        }),
      );
    at(700, () => setBars(true));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, run]);

  const go = (i) => {
    setInstant(false);
    setIdx(i);
    setRun((r) => r + 1);
  };

  const tone = FLAG_TONE[d.flag];
  const nb = d.flag !== "normal" ? d.boxes.length : 0;
  const rowCls = (k) => "wrow" + (rowsIn[k] ? " in" : "");

  return (
    <section className="sec" id="sec-leaf">
      <div className="sechead rv">
        <h2>Nine specimens, nine records.</h2>
        <span className="docaddr">Reference set</span>
      </div>
      <p className="lede rv">
        Step through the fields the pipeline has already analysed. Each one is a
        real record in the chain below.
      </p>

      <div className="leafgrid rv">
        <div className="leafmain">
          <Plate id="leaf-plate" leaf={d} runKey={run} instant={instant} />

          <div className="stepper" id="stepper" role="group" aria-label="Record leaves">
            {leaves.map((leaf, i) => (
              <button
                className="step"
                key={leaf.id}
                type="button"
                data-flag={leaf.flag === "normal" ? "clear" : "flagged"}
                aria-current={String(i === idx)}
                aria-label={
                  "Leaf " +
                  pad2(i + 1) +
                  ", " +
                  leaf.title +
                  ", " +
                  FLAG_LABEL[leaf.flag]
                }
                onClick={() => go(i)}
              >
                <span className="num">{pad2(i + 1)}</span>
                <span className="nm">{leaf.short}</span>
                <span className="fl"></span>
              </button>
            ))}
          </div>

          <div className="actions">
            <button className="cta2" type="button" onClick={() => go(idx)}>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                aria-hidden="true"
              >
                <path
                  d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Re-run this leaf
            </button>
          </div>
        </div>

        <aside className="witness" aria-label="Analysis record">
          <div className="withead">
            <h3>Witness</h3>
            <span id="witleaf">
              Leaf {pad2(idx + 1)} / {pad2(leaves.length)}
            </span>
          </div>
          <p className="sr" id="live" role="status" aria-live="polite">
            Leaf {pad2(idx + 1)} of {pad2(leaves.length)}, {d.title}. Confluency{" "}
            {d.confluency.toFixed(1)} percent. QC flag {FLAG_LABEL[d.flag]} at
            confidence {d.qcConf.toFixed(3)}. Recommended action{" "}
            {ACTION_LABEL[d.action]}.
          </p>

          <div className="witbody" id="witbody">
            <div className={rowCls(0)} data-w="1">
              <p className="wlabel">Confluency</p>
              <p className="big">
                <Counter
                  to={d.confluency}
                  delay={520}
                  runKey={`${idx}:${run}`}
                />
                <sup>%</sup>
              </p>
              <div className="bar">
                <i
                  id="conf-bar"
                  style={{
                    transform: bars
                      ? `scaleX(${d.confluency / 100})`
                      : "scaleX(0)",
                    background:
                      d.confluency >= 80 ? "var(--v-green)" : "var(--bone-2)",
                  }}
                ></i>
                <u style={{ left: "80%" }}></u>
              </div>
              <p className="wmeta">
                {d.method} · confidence {d.confluencyConf.toFixed(3)} · target 80%
              </p>
            </div>

            <div className={rowCls(1)} data-w="2">
              <p className="wlabel">QC flag</p>
              <p className="verdict" id="verdict" data-v={tone}>
                <span className="vdot" aria-hidden="true"></span>
                <span className="vname">{FLAG_LABEL[d.flag]}</span>
                <span className="vconf">{d.qcConf.toFixed(3)}</span>
              </p>
              <div className="probs" id="probs">
                {CLASSES.map((c) => (
                  <div
                    className={"prow" + (c === d.flag ? " on" : "")}
                    key={c}
                    data-v={c === d.flag ? tone : undefined}
                  >
                    <span className="pname">{FLAG_SHORT[c]}</span>
                    <span className="ptrack">
                      <i
                        style={{
                          transform: bars
                            ? `scaleX(${Math.max(d.probs[c], 0.004)})`
                            : "scaleX(0)",
                        }}
                      ></i>
                    </span>
                    <span className="pval">
                      {(d.probs[c] * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
              <p className="wmeta">
                {nb
                  ? nb +
                    " evidence region" +
                    (nb > 1 ? "s" : "") +
                    " marked on the image"
                  : "No evidence regions marked — flag is normal"}
              </p>
            </div>

            <div className={rowCls(2)} data-w="3">
              <p className="wlabel">Recommended action</p>
              <p>
                <span className="badge" data-v={ACTION_TONE[d.action]}>
                  {ACTION_LABEL[d.action]}
                </span>
              </p>
              <p className="wmeta">{d.actionReason}</p>
            </div>

            <div className={rowCls(3)} data-w="4">
              <p className="wlabel">Rationale</p>
              <p className="rationale">{d.rationale}</p>
            </div>

            <div className={rowCls(4)} data-w="5">
              <p className="wlabel">Audit record</p>
              <dl>
                <div className="hashline">
                  <dt>Image</dt>
                  <dd>{d.record.image_hash}</dd>
                </div>
                <div className="hashline">
                  <dt>Prev</dt>
                  <dd className="link">{d.record.prev_record_hash}</dd>
                </div>
                <div className="hashline">
                  <dt>This</dt>
                  <dd>{d.record.record_hash}</dd>
                </div>
              </dl>
              <p className="wmeta">
                seg {d.record.model_versions.seg} · qc{" "}
                {d.record.model_versions.qc} · {d.record.decided_by}
              </p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
