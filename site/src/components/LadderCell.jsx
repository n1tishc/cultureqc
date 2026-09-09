import { FLAG_LABEL } from "../lib/labels";

/* One tile of the severity matrix, with its Grad-CAM boxes drawn over it.
   Shared by the overview's single-line teaser and the full four-line grid. */
export default function LadderCell({ cell, line, sev }) {
  return (
    <div className="ladcell" data-flag={cell.flag}>
      <img
        src={cell.img}
        loading="lazy"
        decoding="async"
        alt={
          line +
          " " +
          (sev === "clean" ? "clean control" : sev + " contamination") +
          " — classified " +
          FLAG_LABEL[cell.flag]
        }
      />
      {cell.flag !== "normal" &&
        cell.boxes.map((b, i) => (
          <div
            className="ebox"
            key={i}
            style={{
              left: b.x * 100 + "%",
              top: b.y * 100 + "%",
              width: b.w * 100 + "%",
              height: b.h * 100 + "%",
            }}
          ></div>
        ))}
      <div className="tag">
        <span>{cell.flag === "normal" ? "Normal" : "Flagged"}</span>
        <i>{cell.conf.toFixed(3)}</i>
      </div>
    </div>
  );
}
