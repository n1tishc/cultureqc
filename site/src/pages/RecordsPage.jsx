import { useEffect, useState } from "react";
import Records, { GmpBoundary } from "../components/Records";
import { Integration } from "../components/Sections";
import { CtaBand, Footer, PageHead, TopBar } from "../components/Shell";
import { Glance, Section, short } from "../components/ui";
import { verifyChain } from "../lib/verify";

/* The records: the stored chain re-hashed in this browser with the tamper switches, where the records stop and the
   host platform starts, and the one call that writes them. Every number is read from data.json or computed here. */
export default function RecordsPage({ data }) {
  const ex = data.examples;
  const [verify, setVerify] = useState(null);
  const [verificationError, setVerificationError] = useState(false);

  useEffect(() => {
    const byId = Object.fromEntries([...ex.items, ...(ex.changes || [])].map((e) => [e.id, e.record]));
    verifyChain(ex.chain_order.map((id) => byId[id])).then(setVerify).catch(() => setVerificationError(true));
  }, [ex]);

  const n = ex.chain_order.length;
  const ok = verify ? verify.filter((v) => v.ok).length : null;
  const stored = JSON.parse(ex.items[0].record.canonical).schema_version;
  const items = [
    {
      href: "#chain",
      label: "Re-hashed in your browser",
      value: verificationError ? "Verification unavailable" : verify ? `${ok} of ${n} verified` : "re-hashing…",
      note: `Each stored record’s SHA-256, recomputed from its bytes, and its link to the one before. Checkpoint head ${short(ex.checkpoint.head_hash, 8)}.`,
    },
    {
      href: "#gmp",
      label: "One chain, two stored record kinds",
      value: "reading · change",
      note: "The schema also supports review events, but this stored chain contains none. A future review would point to its reading without editing it.",
    },
    {
      href: "#integration",
      label: "Written by one call per image",
      value: "analyze()",
      note: `The live console writes schema ${data.meta.schema}, which adds the model-weights check run before every reading; the stored chain here is ${stored}.`,
    },
  ];

  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <TopBar data={data} page="records" />
      <main id="main">
        <PageHead
          title="Records"
          lede={
            <>
              <p>These stored readings and approved calibration changes form one append-only hash chain. Each record carries the hashes of what it was made from, so a reading can be traced to its image, its model, its rules and its calibration. The schema supports review events, but this chain contains none.</p>
              <Glance items={items} />
            </>
          }
          toc={[
            ["chain", "The chain, re-checked here"],
            ["gmp", "Where this sits for GMP"],
            ["integration", "Integration"],
          ]}
        />
        <Section
          id="chain"
          title="Re-checked in your browser"
          lede={
            <p>
              The home page’s {ex.items.length} readings and the {(ex.changes || []).length} approved profile changes before them, as stored. Flip a switch to tamper with the chain three ways, and see what the chain alone catches and what needs the anchored checkpoint. Pick any record to read it.
            </p>
          }
        >
          <Records examples={ex} data={data} />
        </Section>
        <GmpBoundary />
        <Integration data={data} />
      </main>
      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
