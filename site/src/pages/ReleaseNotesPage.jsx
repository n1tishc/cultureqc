import { ReleaseNotes } from "../components/Sections";
import { CtaBand, Footer, PageHead, TopBar } from "../components/Shell";

export default function ReleaseNotesPage({ data }) {
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <TopBar data={data} page="release-notes" />
      <main id="main">
        <PageHead
          title="Release notes"
          lede={<p>What each release added, and what changed once it was tested on real images. Every number names the file it came from.</p>}
          toc={[
            ["v0-3", "v0.3"],
            ["v0-2", "v0.2"],
          ]}
        />
        <div className="wrap releases">
          <ReleaseNotes data={data} />
        </div>
      </main>
      <CtaBand data={data} />
      <Footer data={data} />
    </>
  );
}
