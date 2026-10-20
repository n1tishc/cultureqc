import { useEffect, useRef, useState } from "react";
import Stage from "../components/Stage";
import Timeline from "../components/Timeline";
import { Accuracy, HowItWorks, Scope, Specs } from "../components/Product";
import { PassageRange } from "../components/DenseTest";
import { row } from "../components/Sections";
import { CtaBand, Footer, TopBar } from "../components/Shell";
import { Section } from "../components/ui";
import { verifyChain } from "../lib/verify";
import { Evidence, HostFit, Pilot, ProductIntro, RecordHandoff, Workflow } from "../components/Journey";

/* Sections that moved to their own pages keep their old links working. */
const MOVED = {
  "#records": "/records#chain",
  "#chain": "/records#chain",
  "#integration": "/records#integration",
  "#validation": "/validation#checks",
  "#limits": "/validation#detectability",
  "#confluency": "/validation#confluency",
  "#changes": "/release-notes",
};

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
        <ProductIntro data={data} />
        <section className="vp-demo" id="demo" aria-label="Explore an analysis">
          <div className="wrap">
            <Stage examples={ex} verify={verify} verifyError={verifyError} liveParity={liveParity} />
            <p className="provenance-line">Research demonstration, not an instruction to actuate a culture. Real microscopy and an explicitly labelled synthetic stress test.</p>
          </div>
        </section>
        <Workflow />
        <HostFit />
        <Evidence data={data} />
        <RecordHandoff />
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
