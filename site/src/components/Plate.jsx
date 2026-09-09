import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { FLAG_LABEL, pad2 } from "../lib/labels";
import { RM, BLANK } from "../lib/motion";

/* The specimen plate: image, cell mask, Grad-CAM evidence boxes, scan sweep.

   The content is rendered from props like anything else. What is *not* state is
   the timeline — `void frame.offsetWidth` between removing and re-adding the
   `running` class is what restarts the scan animation, and no amount of state
   modelling reproduces a forced reflow. That, and the 560/900 ms reveal cascade,
   live in an effect keyed on the leaf, so a leaf change cancels the previous
   run's pending steps exactly the way the old token counter did.

   `fit()` sizes the frame to the specimen's real aspect ratio inside whatever
   room the mat has, capped so a 256px tile is never upscaled into mush. */
export default function Plate({
  id,
  leaf,
  runKey,
  instant,
  fitWidth,
  extraTool,
  /* Touching a layer toggle is a deliberate act; the hero uses it to stop its
     one automatic step rather than yanking the frame out from under someone. */
  onInteract,
}) {
  const frameRef = useRef(null);
  const matRef = useRef(null);
  const [mask, setMask] = useState(false);
  const [box, setBox] = useState(false);
  const [shown, setShown] = useState({ mask: false, boxes: false });

  const drawBoxes = !!leaf && leaf.flag !== "normal";

  const fit = () => {
    const frame = frameRef.current;
    const mat = matRef.current;
    if (!leaf || !frame || !mat || !mat.clientWidth) return;
    const cs = getComputedStyle(mat);
    const W =
      mat.clientWidth -
      parseFloat(cs.paddingLeft) -
      parseFloat(cs.paddingRight);
    const H =
      mat.clientHeight -
      parseFloat(cs.paddingTop) -
      parseFloat(cs.paddingBottom);
    if (!(W > 0)) return;
    /* upscale ceiling: keep a tile from going soft */
    const cap = leaf.w > 256 ? 2.6 : 2.1;
    const narrow =
      window.matchMedia("(max-width:1080px)").matches || fitWidth;
    const s =
      narrow || !(H > 0)
        ? Math.min(W / leaf.w, cap)
        : Math.min(W / leaf.w, H / leaf.h, cap);
    frame.style.width = Math.round(leaf.w * s) + "px";
    frame.style.height = Math.round(leaf.h * s) + "px";
  };

  /* Before paint, so the frame is never briefly the previous leaf's shape. */
  useLayoutEffect(fit, [leaf, fitWidth]);

  useEffect(() => {
    let t = 0;
    const onResize = () => {
      clearTimeout(t);
      t = setTimeout(fit, 120);
    };
    const observer = new ResizeObserver(onResize);
    if (matRef.current) observer.observe(matRef.current);
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(t);
      observer.disconnect();
      window.removeEventListener("resize", onResize);
    };
  });

  /* The run. Restart the sweep, reset the overlays, then bring them back on the
     cascade. Cleanup cancels everything pending, so a fast stepper never lets an
     old run's timer paint over the new leaf. */
  useEffect(() => {
    if (!leaf) return undefined;
    const frame = frameRef.current;

    /* The Resting Frame Rule: the segmentation is the confluency measurement,
       so it stays on the field at rest — hiding it on a flagged leaf would hide
       the evidence for one of the two readings printed beside it. The evidence
       boxes are the QC classifier's, and appear only when it raised something. */
    setMask(true);
    setBox(drawBoxes);
    setShown({ mask: false, boxes: false });

    frame.classList.remove("running");
    void frame.offsetWidth;
    const quick = RM.matches || instant;
    if (!quick) frame.classList.add("running");

    const timers = [];
    const at = (ms, fn) => timers.push(setTimeout(fn, quick ? 0 : ms));
    at(560, () => setShown((s) => ({ ...s, mask: true })));
    at(900, () => setShown((s) => ({ ...s, boxes: drawBoxes })));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaf, runKey]);

  const alt = leaf
    ? "Phase-contrast micrograph — " +
      leaf.title +
      " (" +
      leaf.kind +
      "), classified " +
      FLAG_LABEL[leaf.flag] +
      ", confluency " +
      leaf.confluency.toFixed(1) +
      " percent"
    : "Phase-contrast micrograph of a cell culture";

  return (
    <figure className="plate" id={id}>
      <div className="mat" ref={matRef}>
        <div
          className="frame"
          ref={frameRef}
          data-mask={shown.mask ? "on" : "off"}
          data-boxes={shown.boxes ? "on" : "off"}
          style={{ "--nw": leaf ? leaf.w : 704, "--nh": leaf ? leaf.h : 520 }}
        >
          <img className="specimen" alt={alt} src={leaf ? leaf.img : BLANK} />
          <img
            className="masklayer"
            alt=""
            aria-hidden="true"
            src={leaf ? leaf.mask : BLANK}
          />
          <div className="boxes">
            {drawBoxes &&
              leaf.boxes.map((b, k) => (
                <div
                  className="ebox"
                  key={k}
                  style={{
                    left: b.x * 100 + "%",
                    top: b.y * 100 + "%",
                    width: b.w * 100 + "%",
                    height: b.h * 100 + "%",
                    transitionDelay: k * 80 + "ms",
                  }}
                >
                  <b>
                    {"E" +
                      pad2(k + 1) +
                      (leaf.w > 256 || leaf.h > 256
                        ? " · analysed region, centre 256×256"
                        : "")}
                  </b>
                </div>
              ))}
          </div>
          <div className="scan" aria-hidden="true"></div>
        </div>
      </div>
      <figcaption className="platebar">
        <div className="toggles" role="group" aria-label="Overlay layers">
          <label className="tog">
            <input
              type="checkbox"
              data-t="mask"
              checked={mask}
              onChange={(e) => {
                setMask(e.target.checked);
                setShown((s) => ({ ...s, mask: e.target.checked }));
                if (onInteract) onInteract();
              }}
            />
            <span className="dot" aria-hidden="true"></span>Cell mask
            <i className="tstate">{shown.mask ? "shown" : "hidden"}</i>
          </label>
          <label className="tog">
            <input
              type="checkbox"
              data-t="box"
              disabled={!drawBoxes}
              checked={box}
              onChange={(e) => {
                setBox(e.target.checked);
                setShown((s) => ({ ...s, boxes: e.target.checked }));
                if (onInteract) onInteract();
              }}
            />
            <span className="dot" aria-hidden="true"></span>Evidence boxes
            <i className="tstate">
              {!drawBoxes ? "none" : shown.boxes ? "shown" : "hidden"}
            </i>
          </label>
          {extraTool}
        </div>
        {/* The two layers are controlled independently, so the state where they
            coincide has to be named rather than left to be noticed. */}
        <span
          className="layerstate"
          data-layers={
            shown.mask && shown.boxes
              ? "both"
              : shown.mask
                ? "mask"
                : shown.boxes
                  ? "evidence"
                  : "none"
          }
        >
          {shown.mask && shown.boxes
            ? "Overlaid — segmentation and evidence on the same field"
            : shown.mask
              ? "Segmentation only"
              : shown.boxes
                ? "Evidence only"
                : "Field as captured"}
        </span>
        <span className="platecap">
          {leaf && (
            <>
              {leaf.title} &middot; <i>{leaf.kind}</i> &middot; {leaf.w}&times;
              {leaf.h}
            </>
          )}
        </span>
      </figcaption>
    </figure>
  );
}
