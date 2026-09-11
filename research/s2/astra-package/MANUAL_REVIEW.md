# How the visual references were chosen

The scripts reproduce presentation and extraction, not the interpretive act of choosing an event reference. This file makes that manual step explicit.

1. Inspect the full source around the event, including Kirk and the person being examined. Use surrounding frames to distinguish ordinary movement from the first abrupt change.
2. Bracket the first clear abrupt visible movement of Kirk, retaining a small range rather than treating one selected frame as an exact impact measurement.
3. Inspect the other person's hand in the same continuous view. Record observable changes first, such as hand emergence, contact, unfolding, and lowering. Avoid substituting a functional label such as “trigger press” unless the control and its change of state are visible.
4. Preserve the file-specific timestamp and zero-based frame index. Do not use the gunshot-like sound alone as a universal clock or assume that frame number divided by nominal frame rate is always the correct file time.

Useful reference neighborhoods for independent inspection:

| Source | Zero-based frame neighborhood | Selected approximate marker |
|---|---|---|
| 2.MOV | 498–502 | 8.35 s |
| kirk2.mp4 | 183–185 | 6.31 s |
| 7.mp4 | 759–763 | 25.37 s |

These neighborhoods are inspection leads. The report's broader reference windows are manual brackets, not comprehensive physical error bounds. The continuous source footage is included in the companion source bundle. The main review sheets crop toward the men's movements, so they should not alone be used to independently establish the Kirk reference.

For example, extract a full source frame without the report's target crop:

```bash
ffmpeg -i inputs/downloaded/2.MOV -vf "select=eq(n\,500)" -frames:v 1 reference-frame-500.png
```

FFmpeg applies the MOV's display rotation metadata by default. Standard decoding and color conversion occur; a PNG is a lossless record of that decoded output, not a claim that the original compressed HDR pixel values have been preserved verbatim.

No statistical gesture-frequency estimate, blinded reviewer comparison, facial identification, or device recognition model was used. A second reviewer may choose slightly different onset brackets; the stated uncertainty and the distinction between visible ordering and physical timing should be retained.
