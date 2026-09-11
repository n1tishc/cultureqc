export default function NotFound() {
  return (
    <div className="page supporting not-found">
      <h1>That page doesn&rsquo;t exist</h1>
      <p className="lede">
        There&rsquo;s no route at this address. It may have moved, or the link
        may be wrong.
      </p>
      <div className="actions">
        <a className="button primary" href="#/home">
          Go to Home
        </a>
        <a className="button secondary" href="#/demo">
          Explore the demo
        </a>
        <a className="button secondary" href="#/upload">
          Upload your data
        </a>
      </div>
    </div>
  );
}
