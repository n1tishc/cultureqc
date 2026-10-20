import { DenseTest } from "../components/DenseTest";
import { Profiles } from "../components/Profiles";
import { Confluency, Detectability } from "../components/Sections";
import { CtaBand, Footer, PageHead, TopBar } from "../components/Shell";
import { Glance as GlanceList, Path } from "../components/ui";

/* The page's three headline results, each linking to its section: what a
   reader should know before the tables. Every number is read from data.json. */
function Glance({ data }) {
  const msc = data.profiles && data.profiles.items.find((p) => p.id === "msc_phase");
  const mscDense = msc?.bands?.find((band) => band.band === "60-90%");
  const d = data.dense_test;
  const items = [
    d && {
      href: "#dense",
      label: "Fine-tuning: closer confluency readings",
      value: `${d.both.C.B1_mae.toFixed(2)} → ${d.both.F.B1_mae.toFixed(2)} pp`,
      note: `${Math.round((1 - d.both.F.B1_mae / d.both.C.B1_mae) * 100)}% lower mean error versus the calibrated base model on ${d.points.length} mCellSeg images. Pooled secondary analysis, one lab; not a v2 release benchmark. Not used for recommendations: decision agreement is below criterion and the swapped primary comparison did not replicate.`,
    },
    msc && {
      href: "#profiles",
      label: "MSC calibration against expert masks",
      value: `${msc.shipped.mae.toFixed(2)} → ${msc.profile.mae.toFixed(2)} pp`,
      note: `${msc.n_test} MSC images, leave one population out. Default versus calibrated cutoff within this study. ${mscDense ? `Only ${mscDense.n} images at 60–90%, so passage-range criteria were not measurable.` : "Dense-range sample counts are unavailable here; check the source before interpreting action readiness."}`,
    },
    {
      href: "/records#chain",
      label: "An audit trail you can inspect",
      value: `${data.examples.chain_order.length} linked records`,
      note: "Recompute SHA-256 in your browser, alter a local reading and inspect the broken link. Demonstrates record integrity—not biological validity, signed identity or regulatory compliance.",
    },
  ];
  return (
    <>
      <GlanceList items={items} />
      <p className="sources">Sources: <Path>results/confluency_profiles.md</Path> · <Path>results/confluency_mcellseg.md</Path> · <Path>results/confluency_mcellseg_swap.md</Path>. <a href="/records#chain">Inspect the stored record chain</a>.</p>
    </>
  );
}

export default function ValidationPage({ data }) {
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <TopBar data={data} page="validation" />
      <main id="main">
        <PageHead
          title="Better readings. Inspectable evidence."
          lede={
            <>
              <p>Start with what improved: confluency readings closer to expert masks, calibration for the imaging setup, and records your team can verify. The studies below separate measured gains from the work still needed before automated action.</p>
              <Glance data={data} />
            </>
          }
          toc={[
            ...(data.dense_test ? [["dense", "Fine-tuning results"]] : []),
            ...(data.profiles ? [["profiles", "Setup calibration"]] : []),
            ["confluency", "Confluency against expert masks"],
            ["detectability", "Detection scope and next improvements"],
          ]}
        />
        <DenseTest data={data} />
        <Profiles data={data} />
        <Confluency data={data} />
        <div id="checks">
          <Detectability data={data} />
        </div>
      </main>
      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
