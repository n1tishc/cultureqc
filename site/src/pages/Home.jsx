import { useEffect, useState } from "react";
import Stage from "../components/Stage";
import Timeline from "../components/Timeline";
import Records from "../components/Records";
import { Accuracy, HowItWorks, Scope, Specs } from "../components/Product";
import { Integration, row } from "../components/Sections";
import { CtaBand, Footer, TopBar } from "../components/Shell";
import { Icon, Section } from "../components/ui";
import { verifyChain } from "../lib/verify";

/* Sections that moved to their own pages keep their old links working. */
const MOVED = {
  "#validation": "/validation#checks",
  "#limits": "/validation#detectability",
  "#confluency": "/validation#confluency",
  "#changes": "/release-notes",
};

export default function Home({ data }) {
  const [verify, setVerify] = useState(null);
  const ex = data.examples;

  useEffect(() => {
    const to = MOVED[window.location.hash];
    if (to) window.location.replace(to);
  }, []);

  useEffect(() => {
    const byId = Object.fromEntries(ex.items.map((e) => [e.id, e.record]));
    // verifyChain runs in chain order; the stage looks results up by record index.
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
                <a className="btn btn-quiet btn-lg" href="#records">
                  Verify the records <Icon name="down" />
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

        <Section
          id="timeline"
          title="Follow a flask from seeding to passage"
          lede={
            <p>
              {data.replays.length} held-out C2C12 flasks, recorded time-lapse replayed as visits of {data.replays[0].visits[0].fov.length} fields each. The quality gate drops bad images from the trend, the anomaly check flags frames, and a flagged visit holds the passage forecast for a person. {data.replays[0].target_note}
            </p>
          }
        >
          <Timeline replays={data.replays} />
        </Section>

        <Section
          id="records"
          title="Every call, on a record you can re-check"
          lede={
            <p>
              The {ex.items.length} readings above are one hash chain. Your browser has just re-hashed each record from its stored bytes and checked every link. Flip a switch to tamper with it three ways, and see what the chain alone catches and what needs the anchored checkpoint.
            </p>
          }
        >
          <Records examples={ex} />
        </Section>

        <Integration data={data} />
        <Specs data={data} verify={verify} />
        <Scope data={data} />
      </main>

      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
