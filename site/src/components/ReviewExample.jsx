import { useEffect, useState } from "react";
import { verifyReviewDemo } from "../lib/review-verification";
import { Section } from "./ui";

export default function ReviewExample({ examples }) {
  const [result, setResult] = useState(null);
  const [retry, setRetry] = useState(0);
  const demo = examples.review_demo;
  let event = null;
  try {
    event = JSON.parse(demo?.record?.canonical);
  } catch {
    event = null;
  }

  useEffect(() => {
    let active = true;
    setResult(null);
    verifyReviewDemo(examples)
      .then((value) => { if (active) setResult(value); })
      .catch(() => { if (active) setResult({ ok: false }); });
    return () => { active = false; };
  }, [examples, retry]);

  return (
    <Section id="review-example" title="A review adds a record. It never replaces the reading."
      lede={<p>Illustrative workflow only—not a real review, signature or approval. The original stored chain above remains unchanged. This separate demonstration extends a copy with one review event.</p>}>
      <p><a href="/records?record=evican_ht29#chain">Inspect the original HT29 reading</a>: its band crosses the target, so the stored result asks for human review.</p>
      {event?.reviewer ? <p><strong>{event.reviewer.name}</strong> retains <code>{event.final_action}</code>. {event.reason} The identity and timestamps are fictional; <code>host_signature_ref</code> is null. A real host must supply authenticated identity and signatures.</p> : null}
      <p role="status">{result === null ? "Checking the illustrative extension…" : result.ok
        ? `Verified illustrative extension: ${result.count} records, both checkpoints and the exact reading reference match. This verifies bytes, not a person's identity or a scientific decision.`
        : "Could not verify the illustrative extension. Do not rely on this demonstration; retry or inspect the source artifacts."}</p>
      {result?.ok === false ? <button type="button" className="btn btn-quiet" onClick={() => setRetry((value) => value + 1)}>Retry review verification</button> : null}
      {event ? <details className="disclosure">
        <summary>Inspect the illustrative review JSON</summary>
        <pre className="json" tabIndex={0} aria-label="Illustrative review record">{JSON.stringify({ ...event, record_hash: demo.record.record_hash }, null, 2)}</pre>
      </details> : null}
    </Section>
  );
}
