import { DenseTest } from "../components/DenseTest";
import { Profiles } from "../components/Profiles";
import { Confluency, Detectability, Validation } from "../components/Sections";
import { CtaBand, Footer, PageHead, TopBar } from "../components/Shell";

/* The page's three headline results, each linking to its section: what a
   reader should know before the tables. Every number is read from data.json. */
function Glance({ data }) {
  const v = data.validation;
  const msc = data.profiles && data.profiles.items.find((p) => p.id === "msc_phase");
  const d = data.dense_test;
  const count = (k) => v.filter((x) => x.kind === k).length;
  const items = [
    msc && {
      href: "#profiles",
      label: "Confluency, calibrated per microscope",
      value: `${msc.shipped.mae.toFixed(2)} → ${msc.profile.mae.toFixed(2)} pp`,
      note: `Error against expert masks on ${msc.n_test} held-out stem-cell images, before and after the setup’s own cutoff.`,
    },
    d && {
      href: "#dense",
      label: "The passage range, on a lab no model had seen",
      value: `${d.both.C.B1_mae.toFixed(2)} vs ${d.both.F.B1_mae.toFixed(2)} pp`,
      note: `Shipped vs fine-tuned, ${d.points.length} images. The shipped method sends most dense flasks to a person; fine-tuning reads closer but does not decide.`,
    },
    {
      href: "#checks",
      label: `Checks ${v[0].id}–${v[v.length - 1].id} on held-out time-lapse`,
      value: `${count("pass")} pass · ${count("fail")} fail · ${v.length - count("pass") - count("fail")} other`,
      note: "Each failure changed the product or became a stated limit; the list is under the table.",
    },
  ].filter(Boolean);
  return (
    <ul className="glance">
      {items.map((it) => (
        <li key={it.href}>
          <a href={it.href}>
            <span className="glance-label">{it.label}</span>
            <span className="glance-value num">{it.value}</span>
            <span className="glance-note">{it.note}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

export default function ValidationPage({ data }) {
  const v = data.validation;
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <TopBar data={data} page="validation" />
      <main id="main">
        <PageHead
          title="Validation"
          lede={
            <>
              <p>How cultureQC was tested, on real images held out from every fit: confluency against expert masks, then the per-flask checks on recorded time-lapse, then what it can and cannot see. Three results first.</p>
              <Glance data={data} />
            </>
          }
          toc={[
            ...(data.profiles ? [["profiles", "Confluency calibrated per imaging setup"]] : []),
            ...(data.dense_test ? [["dense", "The passage range, on a lab it had never seen"]] : []),
            ["confluency", "Confluency against expert masks"],
            ["checks", `Checks ${v[0].id}–${v[v.length - 1].id}`],
            ["detectability", "What it can and cannot see"],
          ]}
        />
        <Profiles data={data} />
        <DenseTest data={data} />
        <Confluency data={data} />
        <Validation data={data} />
        <Detectability data={data} />
      </main>
      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
