# Inputs

Original supplied material. Preserve untouched; derived files go under `data/`.

## kirkshooting/

Four files from the public Internet Archive collection
<https://archive.org/download/kirkshooting>, which gathers phone clips of the
10 September 2025 event at Utah Valley University that circulated afterwards.
The collection names files by number. The files are not committed (see
`.gitignore`); run `inputs/fetch.sh` to download and verify them against
`kirkshooting/SHA256SUMS`.

| File | Listed on archive.org | Size | Study alias | What it is (container metadata) |
| --- | --- | --- | --- | --- |
| `2.MOV` | 28 Oct 2025 01:15 | 69.7 MB | k1hq (was `kirk1.mov`) | iPhone 15 Pro camera original, HEVC 1920×1080 rotated to portrait, 59.94 fps, 2204 frames, 36.8 s. QuickTime tags: created 2025-09-10 12:23:19 MDT, location +40.2775 −111.7138 (the UVU campus), iOS 18.6.2. |
| `2.mp4` | 28 Oct 2025 01:23 | 3.5 MB | k1 (was `kirk1.mp4`) | 270×480 H.264 transcode of `2.MOV`, same 2204 frames and audio. Too small for any claim about a hand. |
| `16.mp4` | 29 Sep 2025 02:52 | 1.9 MB | k2 (was `kirk2.mp4`) | 720×1280 H.264 copy, nominal 30 fps but variable (first frame held 204 ms), 299 frames, 10.2 s, container created 2025-09-20. A re-encoded download. |
| `7.mp4` | 11 Sep 2025 07:45 | 45.7 MB | k3 (was `kirk3.mp4`) | 1920×1080 H.264, 29.97 fps, 1176 frames, 39.2 s. Container written by a mobile video editor (`TEEditor` tag) at 2025-09-10 18:46:46 UTC, 23 minutes after the shot. An export, not a camera original. |

The aliases `kirk1`, `kirk2`, `kirk3` are how the files were first named when
this study began; the pages use the archive names.

None of this is a chain of custody. The collection is a convenience copy of
material that was public within hours; the container tags are reported as
found and are not proof of anything on their own.

## astra/

The second review's deliverables, received 11 September 2026 and kept as
delivered:

| File | What it is |
| --- | --- |
| `Kirk_video_review.html` | The review's standalone report with every figure and both slowed clips embedded (10.8 MB). Committed. |
| `Kirk_video_review_GitHub.zip` | The review's repository package: findings, annotations, scripts, audit tables, boards. Not committed; unpacked without the videos and the standalone HTML into `research/s2/astra-package/`. |
| `Kirk_video_sources.zip` | The four source videos again (same SHA-256 as `kirkshooting/`) with the review's own bundle note. Not committed. |
