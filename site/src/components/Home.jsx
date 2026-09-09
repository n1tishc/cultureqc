import { Icon, Status } from "./Workspace";
import { FLAGGED_LEAF } from "../lib/labels";

export default function Home({ leaves }) {
  const sample = leaves[FLAGGED_LEAF];
  return <div className="home-page">
    <section className="home-intro">
      <div className="home-copy">
        <p className="eyebrow"><Icon name="cells" /> CELL CULTURE QUALITY CONTROL</p>
        <h1>A closer look at<br />your cell cultures.</h1>
        <p className="home-description">Measure confluency, review quality flags, and inspect the image evidence behind each result. A focused workspace for microscopy analysis.</p>
        <div className="home-actions"><a className="button primary" href="#/upload"><Icon name="upload" />Upload your data</a><a className="button secondary" href="#/demo">Explore the demo<Icon name="arrow" /></a></div>
        <p className="home-note">Start with a sample dataset or bring your own images.</p>
      </div>
      <figure className="home-specimen">
        <div className="home-image-heading"><span><Icon name="scan" />Phase-contrast microscopy</span><span>DEMO SAMPLE</span></div>
        <img src={sample.img} alt={`${sample.record.cell_line} cell culture, sample microscopy image`} />
        <figcaption><div><span>Cell line</span><strong>{sample.record.cell_line}</strong></div><div><span>Confluency</span><strong>{sample.confluency.toFixed(1)}%</strong></div><div><span>Quality review</span><Status flag={sample.flag} /></div></figcaption>
      </figure>
    </section>
    <section className="home-start" aria-labelledby="start-title">
      <div className="home-section-heading"><p className="eyebrow">GET STARTED</p><h2 id="start-title">Choose your workspace</h2></div>
      <div className="start-grid">
        <a href="#/demo" className="start-card"><span className="start-icon"><Icon name="scan" /></span><div><span className="eyebrow">SAMPLE DATA</span><h3>Explore a complete analysis</h3><p>Browse {leaves.length} recorded specimens. Compare images, toggle segmentation overlays, and inspect quality scores.</p><span className="start-link">Open demo<Icon name="arrow" /></span></div></a>
        <a href="#/upload" className="start-card"><span className="start-icon"><Icon name="upload" /></span><div><span className="eyebrow">YOUR DATA</span><h3>Analyse your own cultures</h3><p>Add microscopy images or a batch, run the analysis, and review results in your own workspace.</p><span className="start-link">Upload images<Icon name="arrow" /></span></div></a>
      </div>
    </section>
    <section className="home-method" aria-label="Analysis workflow">{[["01", "Measure", "Review the proportion of the image covered by cells."], ["02", "Inspect", "Examine quality flags alongside the original image."], ["03", "Trace", "Export records and verify their image-linked audit trail."]].map(([n,title,text]) => <div key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></div>)}</section>
    <p className="home-limitation">For research use. QC models are trained on synthetic data; review predictions alongside your images. <a href="#/provenance">Model details and limitations<Icon name="arrow" /></a></p>
  </div>;
}
