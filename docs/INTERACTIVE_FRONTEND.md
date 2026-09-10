# Interactive microscopy homepage

The home page includes a CSS 3D stack of the existing microscopy image, cell
mask, and QC evidence planes. Visitors can drag or use buttons/arrow keys to
rotate it, align the layers, select a layer, and switch among three recorded
specimens. The inspect action opens that exact specimen in the demo.

This is an exploded view of 2D analysis layers, not a volumetric reconstruction.
All images, masks, coordinates, and readouts come from the existing sample data.
The four-case QC challenge compares a visitor's choice against recorded model
predictions and links to the evidence; agreement is not presented as diagnostic
correctness.

Reduced-motion preferences default to aligned layers and disable transitions
and drag rotation. Buttons remain available. There are no continuous animation
loops, new dependencies, or changes to live model inference.

Validation covered desktop/mobile widths, pointer and keyboard rotation, layer
selection, specimen navigation, both challenge outcomes, reduced-motion behavior,
browser errors, and the production build.
