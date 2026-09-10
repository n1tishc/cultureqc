import { Icon } from "./Workspace";
import MicroscopyPlayground, { SpotCheck } from "./MicroscopyPlayground";

export default function Home({ leaves, onInspect }) {
  return (
    <div className="home-page">
      <section className="home-intro">
        <div className="home-copy">
          <p className="eyebrow">
            <Icon name="cells" /> CELL CULTURE QUALITY CONTROL
          </p>
          <h1>
            Your images.
            <br />A clearer view of culture quality.
          </h1>
          <p className="home-description">
            Measure cell coverage, inspect quality signals, and trace each
            result back to the microscopy image. Explore the layers, then try
            your own sample.
          </p>
          <div className="home-actions">
            <a className="button primary" href="#/upload">
              <Icon name="upload" />
              Upload your data
            </a>
            <a className="button secondary" href="#/demo">
              Explore the demo
              <Icon name="arrow" />
            </a>
          </div>
          <p className="home-note">
            {leaves.length} sample images · Interactive evidence · Research use
          </p>
          <div className="home-capabilities" aria-label="Analysis capabilities">
            <span>
              <Icon name="scan" />
              Confluency
            </span>
            <span>
              <Icon name="layers" />
              Quality review
            </span>
            <span>
              <Icon name="shield" />
              Traceable records
            </span>
          </div>
        </div>
        <MicroscopyPlayground leaves={leaves} onInspect={onInspect} />
      </section>
      <section className="home-start" aria-labelledby="start-title">
        <div className="home-section-heading">
          <p className="eyebrow">FROM IMAGE TO EVIDENCE</p>
          <h2 id="start-title">A focused workflow. At every step.</h2>
        </div>
        <div className="start-grid workflow-cards">
          <a href="#/demo" className="start-card">
            <span className="start-icon">
              <Icon name="scan" />
            </span>
            <div>
              <span className="eyebrow">01 / EXPLORE</span>
              <h3>Start with the evidence</h3>
              <p>
                Browse {leaves.length} recorded specimens. Compare images,
                toggle segmentation overlays, and inspect quality scores.
              </p>
              <span className="start-link">
                Open demo
                <Icon name="arrow" />
              </span>
            </div>
          </a>
          <a href="#/upload" className="start-card">
            <span className="start-icon">
              <Icon name="upload" />
            </span>
            <div>
              <span className="eyebrow">02 / ANALYSE</span>
              <h3>Bring your own images</h3>
              <p>
                Add microscopy images or a batch, run the analysis, and review
                results in your own workspace.
              </p>
              <span className="start-link">
                Upload images
                <Icon name="arrow" />
              </span>
            </div>
          </a>
          <a href="#/audit" className="start-card">
            <span className="start-icon">
              <Icon name="shield" />
            </span>
            <div>
              <span className="eyebrow">03 / VERIFY</span>
              <h3>Follow the record</h3>
              <p>
                Review the analysis record and verify the sample audit trail
                directly in your browser.
              </p>
              <span className="start-link">
                Explore traceability
                <Icon name="arrow" />
              </span>
            </div>
          </a>
        </div>
      </section>
      <SpotCheck leaves={leaves} onInspect={onInspect} />
      <p className="home-limitation">
        For research use. QC models are trained on synthetic data; review
        predictions alongside your images.{" "}
        <a href="#/provenance">
          Model details and limitations
          <Icon name="arrow" />
        </a>
      </p>
    </div>
  );
}
