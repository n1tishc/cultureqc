import { useEffect, useState } from "react";
import DATA from "./data.json";
import Stage from "./components/Stage";
import Timeline from "./components/Timeline";
import Records from "./components/Records";
import { Changes, Confluency, Footer, Integration, Limits, Validation, row } from "./components/Sections";
import { Icon, Section } from "./components/ui";
import { verifyChain } from "./lib/verify";

const NAV = [
  ["reading", "Reading"],
  ["confluency", "Confluency"],
  ["records", "Records"],
  ["integration", "Integration"],
  ["timeline", "Timeline"],
  ["limits", "Limits"],
  ["validation", "Validation"],
  ["changes", "Since v0.2"],
];

/* eslint-disable-next-line no-undef */
const COMMIT = typeof __COMMIT__ !== "undefined" ? __COMMIT__ : "";

function useActiveSection() {
  const [active, setActive] = useState("reading");
  useEffect(() => {
    const els = NAV.map(([id]) => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: "-80px 0px -60% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return active;
}

export default function App() {
  const [verify, setVerify] = useState(null);
  const active = useActiveSection();
  const ex = DATA.examples;

  useEffect(() => {
    const byId = Object.fromEntries(ex.items.map((e) => [e.id, e.record]));
    verifyChain(ex.chain_order.map((id) => byId[id])).then((res) => {
      // verifyChain runs in chain order; the stage looks results up by record index.
      setVerify(res);
    });
  }, [ex]);

  const zg = row(DATA, "Live latency, console Space on ZeroGPU");
  const parity = (zg.number.match(/flag and action the same as stored on \d+ of \d+ examples/) || [""])[0];
  const liveParity = parity ? `On the live console (ZeroGPU), ${parity} (${zg.source}).` : "";

  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="bar">
        <div className="wrap bar-in">
          <a className="mark" href="#reading" aria-label="cultureQC v0.3, top">
            <b>cultureQC</b>
            <span>v0.3 · {DATA.meta.rules}</span>
          </a>
          <nav className="nav" aria-label="Sections">
            {NAV.map(([id, label]) => (
              <a key={id} href={`#${id}`} aria-current={active === id ? "true" : undefined}>
                {label}
              </a>
            ))}
          </nav>
          <a className="btn btn-primary" href={DATA.meta.console_url} target="_blank" rel="noreferrer">
            Live console <Icon name="external" />
          </a>
        </div>
      </header>

      <main id="main">
        <section className="hero" id="reading" aria-labelledby="reading-h">
          <div className="wrap">
            <div className="hero-row">
              <h1 id="reading-h">Confluency QC that shows its evidence</h1>
              <div className="hero-side">
                <p>
                  One phase-contrast image per flask visit in; out comes a confluency reading with a boundary-ambiguity review trigger, a per-image anomaly check and a recommended action, sealed into a hash-chained record. Checked on real C2C12 and EVICAN images, failures stated. For a live run on any image, open the{" "}
                  <a href={DATA.meta.console_url} target="_blank" rel="noreferrer">
                    console
                  </a>
                  .
                </p>
              </div>
            </div>
          </div>
          <div className="wrap" style={{ marginTop: "clamp(12px, 1.4vw, 18px)" }}>
            <Stage examples={ex} verify={verify} liveParity={liveParity} />
            <p className="provenance-line">
              Everything above is the pipeline’s stored output for real frames. The live console runs the same code on any image you give it.
            </p>
          </div>
        </section>

        <Confluency data={DATA} />

        <Section
          id="records"
          title="Every reading is a record you can re-check"
          lede={
            <p>
              The {ex.items.length} readings above are one hash chain. Your browser has just re-hashed each record from its stored bytes and checked every link. Flip a switch to tamper with it three ways, and see what the chain alone catches and what needs the anchored checkpoint.
            </p>
          }
        >
          <Records examples={ex} />
        </Section>

        <Integration data={DATA} />

        <Section
          id="timeline"
          title="Across visits: growth, noise, and a passage that waits for review"
          lede={
            <p>
              {DATA.replays.length} held-out C2C12 flasks, recorded time-lapse replayed as visits of {DATA.replays[0].visits[0].fov.length} fields each. The quality gate drops bad images from the trend, the anomaly check flags frames, and a flagged visit holds the passage forecast for a person. {DATA.replays[0].target_note}
            </p>
          }
        >
          <Timeline replays={DATA.replays} />
        </Section>

        <Limits data={DATA} />
        <Validation data={DATA} />

        <Changes data={DATA} />
      </main>

      <Footer data={DATA} commit={COMMIT} />
    </>
  );
}
