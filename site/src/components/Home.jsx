import Instrument, { NegativeResults } from "./Instrument";
import MicroscopyPlayground from "./MicroscopyPlayground";
import { Icon } from "./Workspace";

export default function Home({ leaves, onInspect }) {
  return (
    <div className="home-page">
      <section className="home-intro">
        <div className="home-copy">
          <p className="eyebrow">
            <Icon name="cells" /> CELL CULTURE QUALITY CONTROL
          </p>
          <h1>
            See the field.
            <br />
            Follow the evidence.
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
        <div className="hero-micrograph">
          <img
            src="/img/Huh7contam.webp"
            alt="Huh7 microscopy field with synthetic contamination"
          />
          <span>HUH7 / PHASE CONTRAST / RESEARCH SPECIMEN</span>
        </div>
      </section>
      <Instrument demo />
      <section className="home-start" aria-labelledby="start-title">
        <div className="home-section-heading">
          <p className="eyebrow">FROM IMAGE TO EVIDENCE</p>
          <h2 id="start-title">A focused workflow. At every step.</h2>
        </div>
        <MicroscopyPlayground leaves={leaves} onInspect={onInspect} />
        <div className="home-start-links">
          <a href="#/upload" className="text-button">
            <Icon name="upload" />
            Bring your own images
            <Icon name="arrow" />
          </a>
          <a href="#/audit" className="text-button">
            <Icon name="shield" />
            Follow and verify the record
            <Icon name="arrow" />
          </a>
        </div>
      </section>
      <NegativeResults />
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
