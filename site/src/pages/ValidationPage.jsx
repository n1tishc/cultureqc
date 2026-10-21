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
      label: "Readings within 5 points of the experts",
      value: `${d.both.within5.F} of ${d.both.F.n}`,
      note: `After fine-tuning on one lab’s labelled images, across ${d.setups} imaging setups, each image unseen in training; ${d.both.within5.C} with calibration alone. Experimental: it decides nothing yet, because decision agreement fell short of its criterion and the swapped comparison did not replicate.`,
    },
    msc && {
      href: "#profiles",
      label: "Average distance from expert outlines, calibrated",
      value: `${msc.profile.mae.toFixed(1)} points`,
      note: `${msc.n_test} human MSC images, against ${msc.shipped.mae.toFixed(1)} points at the default setting; each population tested with calibration fitted on the others. ${mscDense ? `Only ${mscDense.n} were in the 60–90% passage range, so accuracy there is not yet measured.` : "Dense-range sample counts are unavailable here; check the source before interpreting action readiness."}`,
    },
    {
      href: "/records#chain",
      label: "An audit trail you can inspect",
      value: `${data.examples.chain_order.length} linked records`,
      note: "Recompute every SHA-256 in your browser, alter a reading and watch the chain fail. Proves integrity, not biological validity, signed identity or compliance.",
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
