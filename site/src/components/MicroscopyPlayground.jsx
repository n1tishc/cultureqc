import { useEffect, useRef, useState } from "react";
import { Icon, Status } from "./Workspace";
import "./microscopy-playground.css";

const LAYERS = [
  [
    "image",
    "01",
    "Microscopy",
    "The original field. Start with what you can see.",
  ],
  [
    "mask",
    "02",
    "Segmentation",
    "The recorded cell mask used to visualize coverage.",
  ],
  [
    "evidence",
    "03",
    "QC evidence",
    "Regions highlighted by the classifier. These are evidence, not individual cell detections.",
  ],
];

export default function MicroscopyPlayground({ leaves, onInspect }) {
  const [selected, setSelected] = useState(4);
  const [layer, setLayer] = useState("evidence");
  const [separated, setSeparated] = useState(
    () => !matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const scene = useRef(null);
  const drag = useRef(null);
  const angles = useRef({ x: 48, z: -26 });
  const leaf = leaves[selected];
  const paint = () => {
    scene.current?.style.setProperty("--rx", `${angles.current.x}deg`);
    scene.current?.style.setProperty("--rz", `${angles.current.z}deg`);
  };
  const rotate = (amount) => {
    angles.current.z = Math.max(-65, Math.min(65, angles.current.z + amount));
    paint();
  };
  useEffect(() => {
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => {
      setReduced(query.matches);
      if (query.matches) setSeparated(false);
    };
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);
  const reset = () => {
    angles.current = { x: 48, z: -26 };
    paint();
  };

  return (
    <section
      className="micro-playground"
      aria-label="Interactive microscopy layers"
    >
      <div className="micro-topline">
        <span>
          <i />
          THE IMAGE, UNPACKED
        </span>
        <span>INTERACTIVE DEMO</span>
      </div>
      <div
        className="micro-stage"
        ref={scene}
        data-separated={separated}
        data-layer={layer}
        tabIndex={0}
        role="group"
        aria-label="Microscopy layer view. Use left and right arrow keys to rotate."
        onKeyDown={(event) => {
          if (["ArrowLeft", "ArrowRight"].includes(event.key)) {
            event.preventDefault();
            rotate(event.key === "ArrowLeft" ? -10 : 10);
          }
        }}
        onPointerDown={(event) => {
          if (!separated || reduced || event.button !== 0) return;
          drag.current = { x: event.clientX, z: angles.current.z };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          angles.current.z = Math.max(
            -65,
            Math.min(
              65,
              drag.current.z + (event.clientX - drag.current.x) * 0.25,
            ),
          );
          paint();
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <div className="micro-orbit" aria-hidden="true" />
        <div
          className="micro-stack"
          style={{
            "--image-ratio": `${leaf.w} / ${leaf.h}`,
            "--ratio": leaf.w / leaf.h,
          }}
        >
          <div className="micro-plane micro-image">
            <img
              src={leaf.img}
              alt={`${leaf.record.cell_line} microscopy sample`}
              draggable="false"
            />
            <span className="plane-tag">01 / ORIGINAL IMAGE</span>
          </div>
          <div className="micro-plane micro-mask" aria-hidden="true">
            <img src={leaf.mask} alt="" draggable="false" />
            <span className="plane-tag">02 / CELL MASK</span>
          </div>
          <div className="micro-plane micro-evidence" aria-hidden="true">
            {leaf.flag !== "normal" &&
              leaf.boxes.map((box, i) => (
                <i
                  key={i}
                  className="micro-evidence-box"
                  style={{
                    left: `${box.x * 100}%`,
                    top: `${box.y * 100}%`,
                    width: `${box.w * 100}%`,
                    height: `${box.h * 100}%`,
                  }}
                />
              ))}
            <span className="plane-tag">
              03 / {leaf.flag === "normal" ? "NO QC FLAG" : "QC EVIDENCE"}
            </span>
          </div>
        </div>
        <span className="micro-stage-note">
          {separated
            ? reduced ? "Use the rotation controls to explore" : "Drag to rotate · explore the layers"
            : "Aligned view · layers share image coordinates"}
        </span>
        <span className="micro-scale" aria-hidden="true">
          {leaf.w} × {leaf.h} PX
        </span>
      </div>
      <div className="micro-controls">
        <button
          className="micro-depth"
          aria-pressed={separated}
          onClick={() => setSeparated(!separated)}
        >
          <Icon name="layers" />
          {separated ? "Align layers" : "Separate layers"}
        </button>
        <div className="micro-rotation" aria-label="View controls">
          <button
            aria-label="Rotate layers left"
            disabled={!separated}
            onClick={() => rotate(-10)}
          >
            ↶
          </button>
          <button
            aria-label="Rotate layers right"
            disabled={!separated}
            onClick={() => rotate(10)}
          >
            ↷
          </button>
          <button
            aria-label="Reset layer rotation"
            disabled={!separated}
            onClick={reset}
          >
            Reset
          </button>
        </div>
      </div>
      <div
        className="micro-layer-tabs"
        role="group"
        aria-label="Analysis layers"
      >
        {LAYERS.map(([id, n, title]) => (
          <button
            key={id}
            aria-label={title}
            aria-pressed={layer === id}
            onClick={() => setLayer(id)}
          >
            <span aria-hidden="true">{n}</span>
            {title}
          </button>
        ))}
      </div>
      <p className="micro-explanation" aria-live="polite">
        {LAYERS.find(([id]) => id === layer)[3]}
      </p>
      <div
        className="micro-specimens"
        role="group"
        aria-label="Choose a microscopy sample"
      >
        {[0, 4, 6].map((index) => (
          <button
            key={index}
            aria-pressed={selected === index}
            onClick={() => setSelected(index)}
          >
            <img src={leaves[index].img} alt="" />
            <span>
              {["BV2", "Huh7", "Detachment"][[0, 4, 6].indexOf(index)]}
            </span>
          </button>
        ))}
      </div>
      <div className="micro-readout" aria-live="polite">
        <div>
          <small>Recorded confluency</small>
          <strong>
            {leaf.confluency.toFixed(1)}
            <span>%</span>
          </strong>
        </div>
        <Status flag={leaf.flag} />
        <button
          onClick={() => onInspect(selected)}
          aria-label={`Inspect ${leaf.id} in the demo`}
        >
          <Icon name="arrow" />
        </button>
      </div>
      <p className="micro-disclosure">
        2D analysis layers arranged in 3D · precomputed sample results
      </p>
    </section>
  );
}

const CASES = [4, 0, 6, 7];
const ANSWERS = [
  ["normal", "Normal"],
  ["contamination_suspected", "Contamination"],
  ["detachment", "Detachment"],
  ["image_quality", "Image quality"],
];
export function SpotCheck({ leaves, onInspect }) {
  const [round, setRound] = useState(0);
  const [answer, setAnswer] = useState(null);
  const index = CASES[round];
  const leaf = leaves[index];
  return (
    <section className="spot-check" aria-labelledby="spot-title">
      <div className="spot-copy">
        <p className="eyebrow">TRY YOUR EYE</p>
        <h2 id="spot-title">What would you flag?</h2>
        <p>
          Take a look at the sample, make your call, then compare it with the
          recorded model result.
        </p>
        <span className="spot-counter">
          SAMPLE {String(round + 1).padStart(2, "0")} / 04
        </span>
        <p className="spot-caveat">
          An exploration of sample predictions, not a diagnostic test.
        </p>
      </div>
      <div className="spot-image">
        <img
          src={leaf.img}
          alt={`Unlabeled microscopy sample ${round + 1} for quality review`}
          loading="lazy"
        />
        <span>
          {leaf.w} × {leaf.h} px
        </span>
      </div>
      <div className="spot-interaction">
        <p className="spot-question">Your first impression?</p>
        <div className="spot-options">
          {ANSWERS.map(([id, label]) => (
            <button
              key={id}
              aria-pressed={answer === id}
              disabled={answer !== null}
              data-match={answer !== null && leaf.flag === id}
              onClick={() => setAnswer(id)}
            >
              {label}
              {answer !== null && leaf.flag === id && <Icon name="check" />}
            </button>
          ))}
        </div>
        <div className="spot-result" aria-live="polite">
          {answer ? (
            <>
              <strong>
                {answer === leaf.flag
                  ? "You and the model agree."
                  : "The model made a different call."}
              </strong>
              <p>
                Recorded result: {ANSWERS.find(([id]) => id === leaf.flag)[1]}.
                Inspect the evidence to decide whether you agree.
              </p>
              <button
                className="spot-evidence"
                onClick={() => onInspect(index)}
              >
                Inspect this sample
                <Icon name="arrow" />
              </button>
            </>
          ) : (
            <p>Choose a label to reveal the model’s result.</p>
          )}
        </div>
        <button
          className="button secondary spot-next"
          onClick={() => {
            setRound((round + 1) % CASES.length);
            setAnswer(null);
          }}
        >
          Next sample
          <Icon name="arrow" />
        </button>
      </div>
    </section>
  );
}
