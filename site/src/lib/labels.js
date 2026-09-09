/* The vocabulary the pipeline's enum values are rendered as, in one place.
   `tone` values feed data-v attributes that styles.css colours. */

export const FLAG_LABEL = {
  normal: "Normal",
  contamination_suspected: "Contamination suspected",
  detachment: "Detachment",
  image_quality: "Image quality",
};

export const FLAG_SHORT = {
  normal: "Normal",
  contamination_suspected: "Contamination",
  detachment: "Detachment",
  image_quality: "Image quality",
};

export const FLAG_TONE = {
  normal: "normal",
  contamination_suspected: "red",
  detachment: "amber",
  image_quality: "amber",
};

export const ACTION_LABEL = {
  passage: "Passage",
  feed: "Feed",
  hold: "Hold",
  human_review: "Human review",
};

export const ACTION_TONE = {
  passage: "normal",
  feed: "amber",
  hold: "amber",
  human_review: "red",
};

export const CLASSES = [
  "normal",
  "contamination_suspected",
  "detachment",
  "image_quality",
];

export const MORPH = {
  A172: "Flat, spread glioblastoma",
  BT474: "Low-contrast epithelial sheet",
  BV2: "Rounded, high-contrast microglia",
  Huh7: "Tightly packed hepatocytes",
};

/* The one deliberate step the hero takes: the same Huh7 field, clean then
   contaminated. Indices into DATA.leaves. */
export const CLEAN_LEAF = 2;
export const FLAGGED_LEAF = 4;

export const pad2 = (n) => String(n).padStart(2, "0");

export function fmtBytes(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1048576).toFixed(1) + " MB";
}
