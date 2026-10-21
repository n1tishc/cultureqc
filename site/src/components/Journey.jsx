import { Icon, Path } from "./ui";
import "./Journey.css";

export function ProductIntro({ data }) {
  return (
    <section className="vp-opening" id="top" aria-labelledby="top-h">
      <div className="wrap">
        <div className="vp-intro">
          <h1 id="top-h">Read the culture.<br />Understand the next step.</h1>
          <div>
            <p>Passage decisions often rest on a glance down the microscope. cultureQC turns that image into a measured confluency, a recommendation with its reason, and a record anyone can verify.</p>
            <div className="vp-actions">
              <a className="btn btn-primary" href="#demo">Explore an analysis <Icon name="down" /></a>
              <a className="more" href="/records#integration">See how it fits <Icon name="passage" /></a>
            </div>
            <p className="sources">Stored analyses of public microscopy datasets, each record re-hashed in your browser.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* Why it matters, then what each part of the analysis gives a lab. The problem statement is cited; the numbers are
   read from data.json (results/confluency_profiles.md). */
export function Workflow({ data }) {
  const msc = data.profiles?.items.find((item) => item.id === "msc_phase");
  const mid = msc?.bands.find((band) => band.band === "40-60%");
  return (
    <section className="sec product-workflow" aria-labelledby="why-h">
      <div className="wrap">
        <header className="vp-section-head">
          <h2 id="why-h">From a glance to a decision<br />you can defend.</h2>
          <p>Phase contrast is how most labs inspect adherent cultures, and quantifying what it shows by hand is time-consuming and error-prone (<a href="https://doi.org/10.1002/bit.25115" target="_blank" rel="noreferrer">Jaccard et al., 2014</a>). A glance also leaves no record of how the call was made.</p>
        </header>
        <div className="workflow-steps">
          <div>
            <h3>Measured, not eyeballed</h3>
            {mid?.mae0 != null ? (
              <p>Every pixel is classified, then calibrated to the microscope. On <span className="num">{mid.n}</span> human MSC images at 40–60% confluency, the default reading ran <span className="num">{Math.abs(mid.bias0).toFixed(1)}</span> points low; calibrated, it averaged <span className="num">{mid.mae.toFixed(1)}</span> points from the experts.</p>
            ) : <p>Every pixel is classified, then calibrated to the microscope that took the image.</p>}
          </div>
          <div>
            <h3>Knows when it can’t tell</h3>
            <p>Each microscope’s measured error travels with the reading. When that band straddles the target, as on HT29 above, the call goes to a person, with the reason written down.</p>
          </div>
          <div>
            <h3>Provable afterwards</h3>
            <p>Every reading is hash-chained to its image, model, rules and calibration. Change one number and the chain breaks. <a href="/records#chain">Try it on the stored records.</a></p>
          </div>
        </div>
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
        <p>Every stored reading and calibration change sits in one hash chain, re-checked in your browser. Alter a number and watch it fail, or follow HT29 into an illustrative review that adds a record without touching the reading. The hashes prove integrity; the evaluation below is what tests the science.</p>
        <a className="more" href="/records#chain">Verify the chain and try the tamper controls <Icon name="passage" /></a>
      </div>
    </section>
  );
}

export function Evidence({ data }) {
  const profile = data.profiles?.items.find((item) => item.id === "msc_phase");
  const dense = profile?.bands.find((band) => band.band === "60-90%");
  const d = data.dense_test;
  return (
    <section className="sec vp-evidence" id="evidence" aria-labelledby="evidence-h">
      <div className="wrap">
        <header className="vp-section-head">
          {profile ? (
            <h2 id="evidence-h">Within <span className="num-display">{profile.profile.mae.toFixed(1)}</span> points<br />of the experts.</h2>
          ) : <h2 id="evidence-h">Measured against<br />expert outlines.</h2>}
          <p>Scored against cells outlined by hand, on images held out from calibration. Your microscope gets the same test in the evaluation below, before anything acts on a reading.</p>
        </header>
        <div className="evidence-layout">
          <div className="calibration-proof">
            <h3>Calibration · human MSCs</h3>
            {profile ? (
              <>
                <p>Across <span className="num">{profile.n_test}</span> images, readings averaged <strong className="num">{profile.profile.mae.toFixed(2)}</strong> points from the experts’ outlines, against <span className="num">{profile.shipped.mae.toFixed(2)}</span> at the default setting. Each of three cell populations was tested with calibration fitted on the other two.</p>
                <p className="evidence-limit"><strong>The limit:</strong> only <span className="num">{dense?.n ?? "a few"}</span> of these images were in the 60–90% passage range, so accuracy there is not yet measured.</p>
              </>
            ) : <p>Calibration summary unavailable. Consult the full evaluation before interpreting a reading.</p>}
            <a className="more" href="/validation#profiles">Read the protocol and results <Icon name="passage" /></a>
            <p className="sources"><Path>results/confluency_profiles.md</Path></p>
          </div>
          {d ? (
            <div className="calibration-proof">
              <h3>Fine-tuning · one lab, <span className="num">{d.setups}</span> imaging setups</h3>
              <p><strong className="num">{d.both.within5.F} of {d.both.F.n}</strong> readings landed within 5 points of the experts after fine-tuning on the lab’s own labelled images, each tested on an image the model never saw. Calibration alone: <span className="num">{d.both.within5.C}</span>.</p>
              <p className="evidence-limit"><strong>The limit:</strong> experimental, and it decides nothing yet. Its decision agreement near the target fell short of a criterion set in advance, and the swapped-halves repeat of the primary comparison did not replicate.</p>
              <a className="more" href="/validation#dense">See the fine-tuning results <Icon name="passage" /></a>
              <p className="sources"><Path>results/confluency_mcellseg.md</Path> · <Path>results/confluency_mcellseg_swap.md</Path></p>
            </div>
          ) : null}
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
