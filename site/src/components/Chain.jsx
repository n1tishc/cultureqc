import { useRef, useState } from "react";
import { FLAG_LABEL, FLAGGED_LEAF, pad2 } from "../lib/labels";
import { GENESIS, sha256 } from "../lib/hash";
import { RM } from "../lib/motion";

const IconOK = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    aria-hidden="true"
  >
    <path d="M4 12.5l5.2 5.2L20 7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconBad = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    aria-hidden="true"
  >
    <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
  </svg>
);
const IconRun = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    aria-hidden="true"
  >
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" strokeLinecap="round" />
  </svg>
);

const stateIcon = (s) =>
  s === "ok" ? <IconOK /> : s === "bad" ? <IconBad /> : <IconRun />;

const WORDS = [
  "zero", "one", "two", "three", "four", "five", "six",
  "seven", "eight", "nine", "ten", "eleven", "twelve",
];

export default function Chain({ leaves }) {
  /* The canonical bytes are the state, not the records — tampering edits the
     string that gets hashed, exactly as editing a line of the log would. */
  const [canon, setCanon] = useState(() => leaves.map((d) => d.canonical));
  const [tampered, setTampered] = useState(false);
  const [rows, setRows] = useState(() =>
    leaves.map((d) => ({
      s: "idle",
      label: "Not checked",
      digest: d.record.record_hash,
    })),
  );
  const [stat, setStat] = useState({
    s: null,
    node: "Chain not yet verified in this browser",
  });
  const running = useRef(false);

  const tamperFrom = '"confluency_pct":' + leaves[FLAGGED_LEAF].confluency;
  const tamperTo =
    '"confluency_pct":' + (leaves[FLAGGED_LEAF].confluency + 9).toFixed(2);

  async function verify(source) {
    if (running.current) return;
    running.current = true;
    const bytes = source || canon;
    setStat({ s: "run", node: "Recomputing SHA-256 in this browser…" });

    let prev = GENESIS;
    let broken = -1;
    const next = leaves.map((d) => ({
      s: "idle",
      label: "Not checked",
      digest: d.record.record_hash,
    }));

    for (let i = 0; i < leaves.length; i++) {
      next[i] = { ...next[i], s: "run", label: "Hashing" };
      setRows(next.slice());
      /* The pause is the point: a chain that verifies instantly looks like a
         claim, and one you watch resolve line by line looks like a check. */
      if (!RM.matches) await new Promise((r) => setTimeout(r, 110));

      const digest = await sha256(bytes[i]);
      const rec = JSON.parse(bytes[i]);
      const linkOK = rec.prev_record_hash === prev;
      const selfOK = digest === leaves[i].record.record_hash;
      next[i] = {
        s: selfOK && linkOK ? "ok" : "bad",
        label:
          selfOK && linkOK
            ? "Verified"
            : !selfOK
              ? "Digest mismatch"
              : "Link broken upstream",
        digest,
      };
      if (!(selfOK && linkOK) && broken < 0) broken = i;
      setRows(next.slice());
      prev = digest;
    }

    setStat(
      broken < 0
        ? {
            s: "ok",
            node: `Chain intact — ${leaves.length} records verified in your browser`,
          }
        : {
            s: "bad",
            node: `Chain broken at leaf ${pad2(broken + 1)} — every record after it is unprovable`,
          },
    );
    running.current = false;
  }

  async function tamper() {
    const next = canon.slice();
    if (!tampered) {
      next[FLAGGED_LEAF] = next[FLAGGED_LEAF].replace(tamperFrom, tamperTo);
    } else {
      next[FLAGGED_LEAF] = leaves[FLAGGED_LEAF].canonical;
    }
    setCanon(next);
    setTampered(!tampered);
    await verify(next);
  }

  return (
    <section className="sec" id="sec-chain">
      <div className="sechead rv">
        <h2>Don&rsquo;t take the record&rsquo;s word for it. Check it.</h2>
        <span className="docaddr">Audit trail &middot; SHA-256</span>
      </div>
      <p className="lede rv">
        The {WORDS[leaves.length] || String(leaves.length)} records those
        specimens actually wrote. Each carries the SHA-256 of the record before
        it. <strong>Verify recomputes every digest in your browser.</strong> Then
        break one on purpose and watch the chain fail.
      </p>

      <div className="chainctl rv">
        <button className="cta" id="verify-btn" type="button" onClick={() => verify()}>
          <IconOK />
          Verify chain
        </button>
        <button className="cta2" id="tamper-btn" type="button" onClick={tamper}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            aria-hidden="true"
          >
            <path d="M12 4v9m0 4v.5" strokeLinecap="round" />
            <path
              d="M10.3 3.1L2.6 17.4A1.6 1.6 0 0 0 4 19.8h16a1.6 1.6 0 0 0 1.4-2.4L13.7 3.1a1.6 1.6 0 0 0-2.8 0z"
              strokeLinejoin="round"
            />
          </svg>
          {(tampered ? " Restore leaf " : " Tamper with leaf ") +
            pad2(FLAGGED_LEAF + 1)}
        </button>
        <p className="chainstat" id="chainstat" role="status" data-s={stat.s || undefined}>
          {stat.s === "ok" ? <IconOK /> : stat.s === "bad" ? <IconBad /> : null}
          {stat.s === "ok" || stat.s === "bad" ? (
            <span>{stat.node}</span>
          ) : (
            stat.node
          )}
        </p>
      </div>

      <div className="chain rv" id="chainlist">
        {leaves.map((d, i) => (
          <div className="crec" key={d.id} id={"crec-" + i} data-s={rows[i].s}>
            <div className="cidx">{pad2(i + 1)}</div>
            <div className="cbody">
              <p className="cname">
                <span>{d.short}</span>
                <i>{FLAG_LABEL[d.flag]}</i>
                <i>{d.confluency.toFixed(1)}%</i>
                <i className="tp">
                  {tampered && i === FLAGGED_LEAF
                    ? "edited: " +
                      d.confluency.toFixed(2) +
                      "% → " +
                      (d.confluency + 9).toFixed(2) +
                      "%"
                    : ""}
                </i>
              </p>
              <p className="chash">
                <b>prev</b> {d.record.prev_record_hash.slice(0, 24)}…&nbsp;
                <b>hash</b> <span id={"ch-" + i}>{rows[i].digest.slice(0, 24)}…</span>
              </p>
            </div>
            <div className="cstate" id={"cs-" + i}>
              {rows[i].s === "idle" ? (
                rows[i].label
              ) : (
                <>
                  {stateIcon(rows[i].s)}
                  <span>{rows[i].label}</span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
