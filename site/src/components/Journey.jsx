import { Icon, Path } from "./ui";
import "./Journey.css";

export function ProductIntro({ data }) {
  return (
    <section className="vp-opening" id="top" aria-labelledby="top-h">
      <div className="wrap">
        <div className="vp-intro">
          <h1 id="top-h">Read the culture.<br />Understand the next step.</h1>
          <div>
            <p>cultureQC turns a microscopy image into a confluency measurement, a rule-based recommendation and a traceable record for your team to review.</p>
            <div className="vp-actions">
              <a className="btn btn-primary" href="#demo">Explore an analysis <Icon name="down" /></a>
              <a className="more" href="/records#integration">See how it fits <Icon name="passage" /></a>
            </div>
            <p className="sources">Stored analysis walkthrough · Code: MIT.<br />Pipeline commercial use is not cleared, pending review. <a href={`${data.meta.repo_url.replace("/tree/", "/blob/")}/README.md#licences-and-commercial-use`} target="_blank" rel="noreferrer">Component terms and status <Icon name="external" /></a></p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Workflow() {
  return (
    <section className="sec product-workflow" aria-label="From image to review">
      <div className="wrap workflow-steps">
        <div><h2>Measure</h2><p>Inspect the segmented area against the original image. Read coverage with a setup-specific error band when available.</p></div>
        <div><h2>Understand</h2><p>See the stored rule result, its reason and its limits. A recommendation supports review; it is not an instruction to actuate.</p></div>
        <div><h2>Trace</h2><p>Follow the reading to its inputs, configuration and record. <a href="/records">Inspect provenance and check record integrity.</a></p></div>
      </div>
    </section>
  );
}

export function HostFit() {
  return (
    <section className="sec product-fit" id="fit" aria-labelledby="fit-h">
      <div className="wrap">
        <header className="vp-section-head">
          <h2 id="fit-h">An analysis step.<br />Your workflow stays yours.</h2>
          <p>The intended host boundary—not a shipped partner integration. cultureQC provides analysis; your platform retains control.</p>
        </header>
        <ol className="host-flow">
          <li><h3>Host: capture and context</h3><p>Images, sample identity and acquisition schedule.</p><Icon name="passage" /></li>
          <li><h3>cultureQC: analysis</h3><p>Measurement, rule-based recommendation and provenance record.</p><Icon name="passage" /></li>
          <li><h3>Host: review and action</h3><p>Human review, identity, signatures, durable retention and any physical action.</p></li>
        </ol>
        <a className="more" href="/records#integration">Inspect the callable interface and responsibilities <Icon name="passage" /></a>
      </div>
    </section>
  );
}

export function RecordHandoff() {
  return (
    <section className="record-handoff" id="trail" aria-labelledby="trail-h">
      <div className="wrap">
        <h2 id="trail-h">Check the record, not just the explanation.</h2>
        <p>Trace readings and calibration changes, then follow a separately labelled illustrative review. The historical chain is unchanged. Hash verification checks integrity, not scientific validity or compliance.</p>
        <a className="more" href="/records#chain">Verify the chain and try the tamper controls <Icon name="passage" /></a>
      </div>
    </section>
  );
}

export function Evidence({ data }) {
  const profile = data.profiles?.items.find((item) => item.id === "msc_phase");
  const dense = profile?.bands.find((band) => band.band === "60-90%");
  return (
    <section className="sec vp-evidence" id="evidence" aria-labelledby="evidence-h">
      <div className="wrap">
        <header className="vp-section-head">
          <h2 id="evidence-h">Calibration earns its place<br />through measurement.</h2>
          <p>One scoped finding—not a universal accuracy promise. Action eligibility on your instrument still needs evaluation.</p>
        </header>
        <div className="evidence-layout">
          <div className="calibration-proof">
            <h3>Human MSCs · leave-one-population-out evaluation</h3>
            {profile ? (
              <>
                <p>Across <span className="num">{profile.n_test}</span> images, mean absolute error against expert masks was <strong className="num">{profile.profile.mae.toFixed(2)} pp</strong> with setup calibration, versus <span className="num">{profile.shipped.mae.toFixed(2)} pp</span> at the default cutoff. Each population was tested with calibration fitted on the other two.</p>
                <p className="evidence-limit"><strong>The limit:</strong> only <span className="num">{dense?.n ?? "a few"}</span> test images at 60–90% confluency. Dense-range passage criteria were unmeasurable. Calibration does not establish autonomous passage or contamination clearance.</p>
              </>
            ) : <p>Calibration summary unavailable. Consult the full evaluation before interpreting a reading.</p>}
            <a className="more" href="/validation#profiles">Read the protocol and results <Icon name="passage" /></a>
            <p className="sources"><Path>results/confluency_profiles.md</Path></p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Pilot({ data }) {
  return (
    <section className="sec vp-pilot" id="pilot" aria-labelledby="pilot-h">
      <div className="wrap">
        <header className="vp-section-head">
          <h2 id="pilot-h">The next decision:<br />evaluate one setup.</h2>
          <p>Sponsor a bounded offline evaluation—not vessel actuation. Agree what success means before seeing the results.</p>
        </header>
        <div className="pilot-responsibilities">
          <div><h3>Your team brings</h3><ul><li>One named microscope setup and intended decision target.</li><li>Representative images across the relevant density range.</li><li>An agreed independent annotation process.</li></ul></div>
          <div><h3>The proposed readout</h3><ul><li>A protocol frozen before scoring and a held-out comparison.</li><li>Error, decision coverage, review and reimage rates, with limitations.</li><li>Traceable artifacts and a stop, gather-more or proceed recommendation.</li></ul></div>
        </div>
        <div className="pilot-boundary">
          <h3>Define the gate before starting</h3>
          <p>Agree sample size and acceptance thresholds for early passage, missed readiness and useful decided coverage. Measure operator time and end-to-end latency; do not assume savings. Schedule and budget remain to be agreed.</p>
          <p>Start offline. Runtime correctness and provenance gaps must be resolved before a host shadow evaluation. Commercial clearance and production integration are separate gates.</p>
          <div className="vp-actions">
            <a className="btn btn-primary" href="/records#integration">Inspect the host boundary <Icon name="passage" /></a>
            <a className="more" href="/validation">Review all validation evidence <Icon name="passage" /></a>
          </div>
        </div>
        <details className="pilot-terms" id="model-terms">
          <summary>Code licensing is not pipeline clearance</summary>
          <p>The repository code is MIT-licensed. Model weights and datasets carry separate terms; the assembled pipeline is not cleared for commercial use pending review. This is the repository’s stated boundary, not a new legal determination.</p>
          <a href={`${data.meta.repo_url.replace("/tree/", "/blob/")}/README.md#licences-and-commercial-use`} target="_blank" rel="noreferrer">Read the repository’s licensing disclosure <Icon name="external" /></a>
        </details>
      </div>
    </section>
  );
}
