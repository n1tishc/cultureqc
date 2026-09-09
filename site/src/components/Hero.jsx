import { useEffect, useState } from "react";
import Plate from "./Plate";
import Counter from "./Counter";
import {
  ACTION_LABEL,
  ACTION_TONE,
  CLEAN_LEAF,
  FLAGGED_LEAF,
  FLAG_LABEL,
  FLAG_SHORT,
  FLAG_TONE,
} from "../lib/labels";
import { RM } from "../lib/motion";

export default function Hero({ leaves, onGo }) {
  /* Reduced motion gets the destination, not the journey: the flagged field
     directly, with no step and no sweep. */
  const [idx, setIdx] = useState(RM.matches ? FLAGGED_LEAF : CLEAN_LEAF);
  const [run, setRun] = useState(0);
  const [instant, setInstant] = useState(RM.matches);
  const [autoDone, setAutoDone] = useState(RM.matches);
  const d = leaves[idx];

  /* The One Deliberate Step Rule: the same Huh7 field, clean then contaminated,
     once. It is the whole argument for evidence, made without a click — and it
     never repeats, because a loop reads as decoration rather than a result. */
  useEffect(() => {
    if (autoDone || idx !== CLEAN_LEAF) return undefined;
    const t = setTimeout(() => {
      setAutoDone(true);
      setInstant(false);
      setIdx(FLAGGED_LEAF);
      setRun((r) => r + 1);
    }, 3600);
    return () => clearTimeout(t);
  }, [autoDone, idx]);

  return (
    <section className="sec hero" id="sec-hero" aria-label="What cultureQC does">
      <div className="heroL">
        <h1 className="hook">
          One brightfield image in. Four outputs,{" "}
          <em>bound to a record you can prove.</em>
        </h1>
        <p className="subhook">
          A confluency estimate that holds across cell morphologies, a QC flag
          with the pixels that raised it, a recommended action, and a
          hash-chained record. <b>Software, not an instrument:</b> it runs on the
          scope your platform already has.
        </p>

        <div className="readout" id="hero-readout">
          <div className="ro">
            <p className="rok">Confluency</p>
            <p className="rov">
              <Counter to={d.confluency} delay={520} runKey={`${idx}:${run}`} />
              <sup>%</sup>
            </p>
          </div>
          <div className="ro">
            <p className="rok">QC flag</p>
            <p className="rov" id="hero-flag" data-v={FLAG_TONE[d.flag]}>
              <span className="sm">{FLAG_SHORT[d.flag]}</span>
            </p>
          </div>
          <div className="ro">
            <p className="rok">Action</p>
            <p className="rov" id="hero-action" data-v={ACTION_TONE[d.action]}>
              <span className="sm">{ACTION_LABEL[d.action]}</span>
            </p>
          </div>
        </div>

        <p className="herorec">
          <span>Record</span>
          <i title={"record_hash " + d.record.record_hash}>
            {d.record.record_hash.slice(0, 20)}… · seg{" "}
            {d.record.model_versions.seg} · qc {d.record.model_versions.qc}
          </i>
        </p>

        <div className="actions heroacts">
          <button className="cta" type="button" onClick={() => onGo("analysis")}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M4 6h16M4 12h16M4 18h10" strokeLinecap="round" />
            </svg>
            Open the analysis
          </button>
          <button
            className="cta2"
            type="button"
            onClick={() => onGo("analysis", { scrollTo: "sec-upload" })}
          >
            Run your own field
          </button>
        </div>
      </div>

      <div className="heroR">
        <Plate
          id="hero-plate"
          leaf={d}
          runKey={run}
          instant={instant}
          fitWidth
          onInteract={() => setAutoDone(true)}
          extraTool={
            /* a plain button inside the toggle strip: no dot, and it must not
               look checked */
            <button
              className="tog"
              type="button"
              onClick={() => {
                setAutoDone(true);
                setInstant(false);
                setRun((r) => r + 1);
              }}
            >
              Replay
            </button>
          }
        />
        <p className="sr" role="status" aria-live="polite">
          {d.title}. Confluency {d.confluency.toFixed(1)} percent. QC flag{" "}
          {FLAG_LABEL[d.flag]}. Recommended action {ACTION_LABEL[d.action]}.
        </p>
      </div>
    </section>
  );
}
