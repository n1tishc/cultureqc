import { useEffect, useState } from "react";
import Stage from "../components/Stage";
import Timeline from "../components/Timeline";
import { TITLE } from "../components/Stage";
import { Accuracy, HowItWorks, Scope, Specs } from "../components/Product";
import { PassageRange } from "../components/DenseTest";
import { row } from "../components/Sections";
import { CtaBand, Footer, TopBar } from "../components/Shell";
import { Icon, Section, actionWord, short } from "../components/ui";
import { verifyChain } from "../lib/verify";

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
function Trail({ data, verify }) {
  const ex = data.examples;
  const byId = Object.fromEntries([...ex.items, ...(ex.changes || [])].map((e) => [e.id, e]));
  const chain = ex.chain_order.map((id) => byId[id]);
  const ok = verify ? verify.filter((v) => v.ok).length : null;
  return (
    <section className="sec" id="trail" aria-labelledby="trail-h">
      <div className="wrap feature">
        <div className="feature-text">
          <h2 id="trail-h">Every call, on a record you can re-check</h2>
          <p>
            The {ex.items.length} readings above and the {(ex.changes || []).length} approved calibration changes before them are one hash chain. Each record carries the SHA-256 of its image, probability map, calibration profile, configs and model weights, and of the record before it.
          </p>
          <p>Designed to be written into a host platform’s audit trail; not Part 11 compliant on its own.</p>
          <a className="more" href="/records">
            Re-check the chain and tamper with it <Icon name="passage" />
          </a>
        </div>
        <div className="ledger" role="group" aria-label="The stored record chain">
          <div className="ledger-head">
            <span>Record chain</span>
            <span aria-live="polite">{verify ? `${ok} of ${chain.length} re-hashed in your browser` : "re-hashing…"}</span>
          </div>
          <ol>
            {chain.map((e, i) => {
              const r = verify ? verify[i] : null;
              return (
                <li key={e.id} data-ok={r ? String(r.ok) : "pending"}>
                  <span className="num">#{i + 1}</span>
                  <span className="ledger-what">
                    {e.kind === "change" ? `Calibration change · ${e.after.id}` : TITLE[e.id] || e.label}
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
  const ex = data.examples;

  useEffect(() => {
    const to = MOVED[window.location.hash];
    if (to) window.location.replace(to);
  }, []);

  useEffect(() => {
    const byId = Object.fromEntries([...ex.items, ...(ex.changes || [])].map((e) => [e.id, e.record]));
    // verifyChain runs in chain order (approved profile changes first); the stage looks results up by record index.
    verifyChain(ex.chain_order.map((id) => byId[id])).then(setVerify);
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
        <section className="hero" id="top" aria-labelledby="top-h">
          <div className="wrap hero-row">
            <h1 id="top-h">Confluency QC with a traceable record behind every call</h1>
            <div className="hero-side">
              <p>
                cultureQC reads one phase-contrast image per flask visit and returns a confluency reading, a per-image anomaly check and a recommended action. Each result is sealed into a hash-chained record, designed to attach to an existing audit trail.
              </p>
              <div className="hero-actions">
                <a className="btn btn-primary btn-lg" href={data.meta.console_url} target="_blank" rel="noreferrer">
                  Open the live console <Icon name="external" />
                </a>
                <a className="btn btn-quiet btn-lg" href="/records">
                  Verify the records <Icon name="passage" />
                </a>
              </div>
              <p className="hero-meta">
                <span>Cellpose-SAM</span>
                <span>DINOv2-small</span>
                <span>{data.meta.rules}</span>
                <span>MIT licence</span>
              </p>
            </div>
          </div>
          <div className="wrap hero-stage">
            <Stage examples={ex} verify={verify} liveParity={liveParity} />
            <p className="provenance-line">Everything above is the pipeline’s stored output for real frames. The live console runs the same code on any image you give it.</p>
          </div>
        </section>

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

        <Trail data={data} verify={verify} />
        <Specs data={data} verify={verify} />
        <Scope data={data} />
      </main>

      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
