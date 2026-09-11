# Kirk footage: movement and timing

A reproducible, four-source visual review of the sleeve contact and blue-shirted man's hand movements. **A pre-event sleeve contact is visible. Two coordinated device activations are not established.**

Start with [the findings](FINDINGS.md), or open `report/index.html` in a browser for the visual presentation and slowed clips. The separate `Kirk_video_review.html` download is a self-contained copy of the same presentation.

![Sleeve contact, clearer source](report/assets/sleeve_annotated.png)

## Reproduce

Requires Python 3.10 or newer, FFmpeg/ffprobe with HEVC decoding and libx264 encoding, and the pinned Pillow dependency. A font is bundled with its license. No AI model, API key, browser extension, or hosted service is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/review.py all
```

On Windows, activate the environment with `.venv\Scripts\activate`; the Python commands are otherwise the same. Install FFmpeg separately and make `ffmpeg` and `ffprobe` available on PATH.

`all` downloads the two public archive files if missing, verifies all four SHA-256 hashes, enumerates frame timestamps, decodes the configured crops, and rebuilds the report. It stops if any source bytes differ. Network access is needed only to acquire missing public files.

For an entirely offline build, extract the companion `Kirk_video_sources.zip` **into this repository directory**. It supplies the `inputs/` tree, including the two archive files. Then run:

```bash
python scripts/review.py verify
python scripts/review.py build
```

To independently rebuild without overwriting the included report:

```bash
python scripts/review.py build --out verification/report --cache verification/cache
```

Every build records Python, Pillow, FFmpeg, and ffprobe versions in `report/audit/environment.json`. PNG/video byte hashes may differ across decoder, color-conversion, or encoder versions. The fixed source hashes, exact frame indices, crop coordinates, and timestamp tables are the primary reproducibility anchors. A fresh end-to-end build was run for this release; see [VALIDATION.md](VALIDATION.md).

Validate source and output integrity after a build with `python scripts/validate.py`. After editing only the written findings or HTML template, `python scripts/review.py present` refreshes the presentation and checksums using the existing images and clips.

## What is in the package

| Path | Purpose |
|---|---|
| `FINDINGS.md` | Written assessment, timing table, limitations, and source links |
| `report/index.html` | Offline visual report with native video controls |
| `report/assets/` | Three annotated PNG sheets, selected unscaled decoded crops, and two muted clips at approximately one-quarter speed |
| `report/audit/` | All four sources' metadata, frame timestamp CSV/JSON, source checks, manual annotations, build environment, and output checksums |
| `config/sources.json` | Exact source sizes, hashes, filenames, and archive URLs |
| `config/annotations.json` | Manual observation windows, reference windows, frame indices, and crop rectangles |
| `scripts/review.py` | Acquisition, verification, probing, extraction, rendering, and standalone export |
| `assets/report-template.html` | Editable visual report text and styling |
| `inputs/supplied/` | The two supplied copies, retained unchanged |
| `inputs/downloaded/` | The two larger archive files, acquired by the script or supplied in the optional source ZIP |

## Interpret and modify the annotations

Frame indices are **zero-based**. Crop rectangles are `[x, y, width, height]` in the displayed image **after** FFmpeg applies rotation metadata. File presentation timestamps locate frames; no timestamp is asserted to be the exact firing time. Each view has its own approximate reference, not an independently synchronized common clock.

The script deterministically renders **manual annotations**. It does not infer a button press, authenticate an original recording, or automate the conclusions. Changing observations requires reviewing the source and updating `config/annotations.json`, `FINDINGS.md`, and `assets/report-template.html` together.

For direct inspection, find an observation's frame in the timestamp CSV and open that position in the source video. The build's selected crops are lossless PNG files; slowed MP4s are convenient, re-encoded review aids. No generative enhancement, sharpening, motion interpolation, or optical-flow reconstruction is applied. Standard decoder/color conversion still occurs, particularly for the HDR sources.

## Put it on GitHub

The repository ZIP includes the two small supplied sources and all generated review assets. The larger downloaded files and temporary extraction cache are ignored by Git. Keep the companion source ZIP as a GitHub Release asset if you want readers to reproduce without relying on the archive URLs. No repository was created or published as part of this review.

The source manifest does not establish ownership or authenticate the uploader. Source footage and the bundled font retain their existing rights; this package makes no claim to relicense them. The review avoids assigning identities or asserting criminal involvement from gestures.

## Review history

- Initial inspection used `kirk1.mp4` and `kirk2.mp4`.
- `2.MOV` added substantially more spatial detail and narrowed the sleeve timing estimates used in the final assessment.
- `7.mp4` added the earlier view of folded fingers; alignment corrected a preliminary approximately 19-second estimate to approximately 21 seconds.
- Release 1.0 records the final four-source assessment. Superseded working drafts and speculative audio-peak labels are not findings in this release.
