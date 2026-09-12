import { useEffect, useRef, useState } from "react";
import Instrument, { NegativeResults } from "./Instrument";
import MicroscopyPlayground from "./MicroscopyPlayground";
import { Icon } from "./Workspace";
import { FLAGGED_LEAF } from "../lib/labels";
import { RM } from "../lib/motion";

export default function Home({ leaves, onInspect }) {
  const heroLeaf = leaves[FLAGGED_LEAF];
  const heroRef = useRef(null);
  const [overlayVisible, setOverlayVisible] = useState(RM.matches);
  /* Fade the segmentation mask in once the hero is actually on screen, rather
     than the instant it mounts — the reveal is the point, so it should read
     as a reveal even when the section loads already scrolled into view. */
  useEffect(() => {
    if (RM.matches) return undefined;
    const node = heroRef.current;
    if (!node) return undefined;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setOverlayVisible(true);
          io.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    io.observe(node);
    return () => io.disconnect();
  }, []);
  return (
    <div className="home-page">
      <section className="home-intro">
        <div className="home-copy">
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
        <div className="hero-micrograph" ref={heroRef}>
          <img
            src={heroLeaf.img}
            alt="Huh7 microscopy field with synthetic contamination"
          />
          <img
            className={"hero-overlay" + (overlayVisible ? " visible" : "")}
            src={heroLeaf.mask}
            alt=""
            aria-hidden="true"
          />
          <span>HUH7 / PHASE CONTRAST / RESEARCH SPECIMEN</span>
        </div>
      </section>
      <section className="home-start" aria-labelledby="start-title">
        <div className="home-section-heading">
          <p className="kicker">From image to evidence</p>
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
      <Instrument demo />
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
