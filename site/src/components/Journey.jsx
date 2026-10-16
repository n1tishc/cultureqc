import { Icon, Path } from "./ui";
import "./Journey.css";

export function Upgrade({ data }) {
  return (
    <section className="vp-opening" id="top" aria-labelledby="top-h">
      <div className="wrap">
        <div className="vp-intro">
          <h1 id="top-h">From a reading to a decision you can inspect.</h1>
          <div>
            <p>One microscopy image. A confluency reading, a recommended action and the evidence behind it. v0.4 adds setup calibration and measured uncertainty—not a claim of autonomous readiness.</p>
            <div className="vp-actions">
              <a className="btn btn-primary btn-lg" href="#demo">Walk through the evidence <Icon name="passage" /></a>
              <a className="more" href="#pilot">Review the pilot plan <Icon name="down" /></a>
            </div>
          </div>
        </div>
        <div className="upgrade-heading">
          <h2>What changed since v0.2</h2>
          <a href="/release-notes">Full release history <Icon name="passage" /></a>
        </div>
        <table className="upgrade-table">
          <thead><tr><th scope="col">The advance</th><th scope="col">v0.2 · the demonstration</th><th scope="col">v0.4 · the evidence</th></tr></thead>
          <tbody>
            <tr>
              <th scope="row">Measurement</th>
              <td>A synthetic accuracy headline and a default segmentation cutoff.</td>
              <td><strong>Real-image evaluation. Calibration per setup.</strong><span>A way to evaluate your microscope, not a universal accuracy claim. <a href="/validation#profiles">See the calibration evidence</a>.</span></td>
            </tr>
            <tr>
              <th scope="row">Decision boundaries</th>
              <td>A fault classifier and confidence signals that did not hold up on real images.</td>
              <td><strong>Failed signals demoted. Error bands inform the action.</strong><span>Inspect why a person is asked to decide. Useful automation coverage still needs proof. <a href="/release-notes#v0-4">See the policy changes</a>.</span></td>
            </tr>
            <tr>
              <th scope="row">Traceability</th>
              <td>Hash-chained readings already linked the result to its inputs.</td>
              <td><strong>Richer provenance, review and change record types.</strong><span>More context to investigate a decision—not a complete compliant host system. <a href="/records">Inspect the records</a>.</span></td>
            </tr>
          </tbody>
        </table>
        <div className="upgrade-foot">
          <p>Different datasets and protocols: this is not a head-to-head accuracy comparison. <Path>results/v02_headline.md</Path></p>
          <p>Code: MIT · <a href="#model-terms">Model and data terms</a></p>
        </div>
      </div>
    </section>
  );
}

export function Evidence({ data }) {
  const profile = data.profiles?.items.find((item) => item.id === "msc_phase");
  const dense = profile?.bands.find((band) => band.band === "60-90%");
  const scale = profile ? Math.ceil(Math.max(profile.shipped.mae, profile.profile.mae)) : 1;
  return (
    <section className="sec vp-evidence" id="evidence" aria-labelledby="evidence-h">
      <div className="wrap">
        <header className="vp-section-head">
          <h2 id="evidence-h">Better measurement.<br />A bounded claim.</h2>
          <p>The strongest advance is a more credible evaluation. It does not yet establish autonomous passage, contamination clearance or lower operating cost.</p>
        </header>
        <div className="evidence-layout">
          <div className="calibration-proof">
            <h3>What setup calibration changed</h3>
            {profile ? (
              <>
                <p>Mean absolute error against expert masks · percentage points</p>
                <dl className="error-comparison">
                  {[["Default cutoff", profile.shipped.mae], ["Setup-calibrated cutoff", profile.profile.mae]].map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd><span className="error-track" aria-hidden="true"><span style={{ width: `${value / scale * 100}%` }} /></span><b className="num">{value.toFixed(2)} <small>pp</small></b></dd>
                    </div>
                  ))}
                </dl>
                <p>{profile.n_test} MSC images; each population tested with calibration fitted on the other two. This compares calibration within the evaluation—not v2 against v4.</p>
                <p className="evidence-limit"><strong>The limit:</strong> only {dense?.n ?? "a few"} test images at 60–90% confluency. Dense-range passage criteria could not be established.</p>
              </>
            ) : <p>Calibration summary unavailable. Consult the full evaluation before interpreting a reading.</p>}
            <a className="more" href="/validation#profiles">Read the protocol and results <Icon name="passage" /></a>
            <p className="sources"><Path>results/confluency_profiles.md</Path></p>
          </div>
          <div className="readiness-notes">
            <div><h3>Shown in this release</h3><p>Setup-specific calibration, uncertainty-aware rules and verifiable stored records. Calibration does not by itself validate the action range.</p></div>
            <div><h3>Experimental, not deciding</h3><p>Lab-specific fine-tuning improves readings in the reported evaluation, but dense-range criteria and replication remain limiting. The experimental model decides nothing.</p><a href="/validation#dense">See gains and failed criteria together</a></div>
            <div><h3>Not established</h3><p>Autonomous passage, realistic contamination protection, production host integration and commercial clearance. An anomaly result of “not flagged” is not a clean-culture certificate.</p><a href="/validation#detectability">Inspect the detection limits</a></div>
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
          <div><h3>The evaluation returns</h3><ul><li>A frozen protocol and held-out comparison.</li><li>Error, decision coverage, review and reimage rates.</li><li>Traceable artifacts and a stop, gather-more or proceed recommendation.</li></ul></div>
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
          <a href={`${data.meta.repo_url}#licences-and-commercial-use`} target="_blank" rel="noreferrer">Read the repository’s licensing disclosure <Icon name="external" /></a>
        </details>
      </div>
    </section>
  );
}
