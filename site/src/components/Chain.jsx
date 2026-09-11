import { useEffect, useRef, useState } from "react";
import { FLAG_LABEL, FLAGGED_LEAF, pad2 } from "../lib/labels";
import { GENESIS, canonJSON, sha256 } from "../lib/hash";
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

export default function Chain({ leaves, sessionFiles = [] }) {
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
  const [sessionRows, setSessionRows] = useState([]);
  const [stat, setStat] = useState({
    s: null,
    node: "Chain not yet verified in this browser",
  });
  const running = useRef(false);

  const done = sessionFiles.filter((f) => f.result);

  const tamperFrom = '"confluency_pct":' + leaves[FLAGGED_LEAF].confluency;
  const tamperTo =
    '"confluency_pct":' + (leaves[FLAGGED_LEAF].confluency + 9).toFixed(2);

  /* Your own analysed uploads, chained onto this trail's tail the same way the
     Upload page chains its own manifest — recomputed here in the browser, not
     written by whatever produced records 01–{leaves.length}. Nothing here
     claims the original log grew a 10th line; it shows that your record hashes
     the same honest way theirs do, continuing from the same anchor. */
  async function buildSessionChain() {
    let prev = leaves[leaves.length - 1].record.record_hash;
    const next = [];
    for (const f of done) {
      const body = {
        schema_version: "0.2-ingest",
        image_ref: f.name,
        image_hash: f.hash,
        bytes: f.size,
        pixels: f.w && f.h ? f.w + "x" + f.h : null,
        confluency_pct: f.result.record.confluency_pct,
        qc_flag: f.result.record.qc_flag,
        recommended_action: f.result.record.recommended_action,
        prev_record_hash: prev,
      };
      const canonical = canonJSON(body);
      const digest = await sha256(canonical);
      next.push({
        name: f.name,
        confluency: f.result.record.confluency_pct,
        flag: f.result.record.qc_flag,
        prevHash: prev,
        digest,
        s: "ok",
      });
      prev = digest;
    }
    return next;
  }

  /* Renders as soon as an upload is analysed, not only after Verify chain is
     pressed — F8's acceptance is that #/audit already shows the extra record
     on arrival; Verify then re-walks it the same as the demo leaves. */
  useEffect(() => {
    let stale = false;
    buildSessionChain().then((next) => {
      if (!stale) setSessionRows(next);
    });
    return () => {
      stale = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done.length]);

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

    const sessionNext = await buildSessionChain();
    setSessionRows(sessionNext);

    const base =
      broken < 0
        ? `Chain intact — ${leaves.length} records verified in your browser`
        : /* Say what the walk actually found, and no more. Editing one record
             fails that record and the link that reaches back to it; the walk
             then heals, because leaf 07 links to leaf 06's untouched digest.
             Claiming "every record after it is unprovable" is contradicted by
             the rows underneath, which still read Verified. */
          `Chain broken at leaf ${pad2(broken + 1)} — that record and the link after it fail verification`;
    setStat({
      s: broken < 0 ? "ok" : "bad",
      node:
        base +
        (sessionNext.length
          ? `, plus ${sessionNext.length} from your session`
          : ""),
    });
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

      {(done.length > 0 || sessionRows.length > 0) && (
        <div className="session-chain" id="session-chainlist">
          <p className="docaddr session-chain-label">
            Your session &middot; analysed on this visit
          </p>
          {sessionRows.length === 0 ? (
            <p className="foot">
              Hashing your {done.length} analysed{" "}
              {done.length === 1 ? "upload" : "uploads"} into this trail…
            </p>
          ) : (
            <div className="chain rv">
              {sessionRows.map((r, i) => (
                <div
                  className="crec"
                  key={r.name + ":" + i}
                  data-s={r.s}
                  data-session="true"
                >
                  <div className="cidx">{pad2(leaves.length + i + 1)}</div>
                  <div className="cbody">
                    <p className="cname">
                      <span>{r.name}</span>
                      <i>{FLAG_LABEL[r.flag]}</i>
                      <i>{r.confluency.toFixed(1)}%</i>
                    </p>
                    <p className="chash">
                      <b>prev</b> {r.prevHash.slice(0, 24)}…&nbsp;
                      <b>hash</b> {r.digest.slice(0, 24)}…
                    </p>
                  </div>
                  <div className="cstate">
                    <IconOK />
                    <span>Verified</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="foot">
            Hashed and chained onto this trail&rsquo;s tail the same way the
            manifest on the Upload page chains its own rows — recomputed here
            in your browser from your session&rsquo;s analysed uploads, not
            written by whatever produced records above.
          </p>
        </div>
      )}
    </section>
  );
}
