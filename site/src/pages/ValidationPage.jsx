import { Confluency, Detectability, Validation } from "../components/Sections";
import { CtaBand, Footer, PageHead, TopBar } from "../components/Shell";

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
          lede={<p>{data.validation_intro}</p>}
          toc={[
            ["confluency", "Confluency against expert masks"],
            ["checks", `Checks ${v[0].id}–${v[v.length - 1].id}`],
            ["detectability", "What it can and cannot see"],
          ]}
        />
        <Confluency data={data} />
        <Validation data={data} />
        <Detectability data={data} />
      </main>
      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
