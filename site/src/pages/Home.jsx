import { useEffect, useRef, useState } from "react";
import Stage from "../components/Stage";
import Timeline from "../components/Timeline";
import { TITLE } from "../components/Stage";
import { Accuracy, HowItWorks, Scope, Specs } from "../components/Product";
import { PassageRange } from "../components/DenseTest";
import { row } from "../components/Sections";
import { CtaBand, Footer, TopBar } from "../components/Shell";
import { Icon, Section, actionWord, short } from "../components/ui";
import { verifyChain } from "../lib/verify";
import { Evidence, Pilot, Upgrade } from "../components/Journey";

/* Sections that moved to their own pages keep their old links working. */
const MOVED = {
  "#records": "/records",
  "#integration": "/records#integration",
  "#validation": "/validation#checks",
  "#limits": "/validation#detectability",
  "#confluency": "/validation#confluency",
  "#changes": "/release-notes",
};

/* The records, in short: the stored chain as a ledger, each row re-hashed in this browser, and the way to the
   records page with the tamper switches. */
function Trail({ data, verify, verifyError }) {
  const ex = data.examples;
  const byId = Object.fromEntries([...ex.items, ...(ex.changes || [])].map((e) => [e.id, e]));
  const chain = ex.chain_order.map((id) => byId[id]);
  const ok = verify ? verify.filter((v) => v.ok).length : null;
  return (
    <section className="sec" id="trail" aria-labelledby="trail-h">
      <div className="wrap feature">
        <div className="feature-text">
          <h2 id="trail-h">Don’t just trust the explanation. Check the record.</h2>
          <p>
            The {ex.items.length} readings above and the {(ex.changes || []).length} approved calibration changes before them are one hash chain. Each record carries the SHA-256 of its image, probability map, calibration profile, configs and model weights, and of the record before it.
          </p>
          <p>Designed to be written into a host platform’s audit trail; not Part 11 compliant on its own.</p>
          <p>These stored examples contain readings and calibration changes, not a human-review event. The format supports review records; this chain does not demonstrate one.</p>
          <a className="more" href="/records">
            Re-check the chain and tamper with it <Icon name="passage" />
          </a>
        </div>
        <div className="ledger" role="group" aria-label="The stored record chain">
          <div className="ledger-head">
            <span>Record chain</span>
            <span aria-live="polite">{verifyError || (verify ? `${ok} of ${chain.length} re-hashed in your browser` : "re-hashing…")}</span>
          </div>
          <ol>
            {chain.map((e, i) => {
              const r = verify ? verify[i] : null;
              return (
                <li key={e.id} data-ok={r ? String(r.ok) : "pending"}>
                  <span className="num">#{i + 1}</span>
                  <span className="ledger-what">
                    <a href={`/records?record=${encodeURIComponent(e.id)}#chain`}>{e.kind === "change" ? `Calibration change · ${e.after.id}` : TITLE[e.id] || e.label}</a>
                  </span>
                  <span className="ledger-val num">
                    {e.kind === "change" ? "approved" : `${e.confluency.pct.toFixed(1)}% · ${actionWord(e.action).toLowerCase()}`}
                  </span>
                  <code>{short(e.record.record_hash, 6)}</code>
                  <Icon name={r && !r.ok ? "cross" : "check"} />
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}

export default function Home({ data }) {
  const [verify, setVerify] = useState(null);
  const [verifyError, setVerifyError] = useState("");
  const appendix = useRef(null);
  const ex = data.examples;

  useEffect(() => {
    const followHash = () => {
      const hash = window.location.hash;
      const to = MOVED[hash];
      if (to) {
        window.location.replace(to);
        return;
      }
      const target = document.getElementById(hash.slice(1));
      if (target?.tagName === "DETAILS") target.open = true;
      if (target && appendix.current?.contains(target)) {
        appendix.current.open = true;
        requestAnimationFrame(() => target.scrollIntoView());
      }
    };
    followHash();
    window.addEventListener("hashchange", followHash);
    return () => window.removeEventListener("hashchange", followHash);
  }, []);

  useEffect(() => {
    let active = true;
    const byId = Object.fromEntries([...ex.items, ...(ex.changes || [])].map((e) => [e.id, e.record]));
    verifyChain(ex.chain_order.map((id) => byId[id]))
      .then((results) => { if (active) setVerify(results); })
      .catch(() => { if (active) setVerifyError("Verification unavailable. Reload to retry; no match has been confirmed."); });
    return () => { active = false; };
  }, [ex]);

  const zg = row(data, "Live latency, console Space on ZeroGPU");
  const parity = (zg.number.match(/flag and action the same as stored on \d+ of \d+ examples/) || [""])[0];
  const liveParity = parity ? `On the live console (ZeroGPU), ${parity} (${zg.source}).` : "";

  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <TopBar data={data} page="home" />

      <main id="main">
        <Upgrade data={data} />
        <section className="vp-demo" id="demo" aria-labelledby="demo-h">
          <div className="wrap">
            <header className="vp-section-head">
              <h2 id="demo-h">Three cases. Follow the decision.</h2>
              <p>Stored pipeline output, not live inference. Start at the uncertainty boundary; inspect the evidence and its exact record.</p>
            </header>
            <Stage examples={ex} verify={verify} verifyError={verifyError} liveParity={liveParity} />
            <p className="provenance-line">Research demonstration, not an instruction to actuate a culture. Real microscopy and an explicitly labelled synthetic stress test.</p>
          </div>
        </section>
        <Evidence data={data} />
        <Trail data={data} verify={verify} verifyError={verifyError} />
        <Pilot data={data} />
        <details className="technical-appendix" ref={appendix}>
          <summary>Explore the technical detail <span>Pipeline, full accuracy figures, flask replays and specifications</span></summary>
        <HowItWorks data={data} />
        <Accuracy data={data} />
        <PassageRange data={data} />

        <Section
          id="timeline"
          title="Follow a flask, visit by visit"
          lede={
            <>
              <p>
                {data.replays.length} held-out C2C12 flasks, replayed as visits of {data.replays[0].visits[0].fov.length} fields each. Bad images drop out of the growth trend, and a flagged visit holds the passage forecast for a person.
              </p>
              <p className="sources">{data.replays[0].target_note}</p>
            </>
          }
        >
          <Timeline replays={data.replays} />
        </Section>

        <Specs data={data} verify={verify} />
        <Scope data={data} />
        </details>
      </main>

      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
