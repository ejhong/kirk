# Release validation

The release was built from the four hash-verified video files using a new extraction cache. It did not reuse the earlier working draft's crops or slowed clips. The report was then refreshed after correcting relative image links in its copy of the written findings.

## Checks completed

- SHA-256 and byte-size verification passed for all four input files.
- ffprobe enumerated 2,204 frames in `kirk1.mp4`, 299 in `kirk2.mp4`, 2,204 in `2.MOV`, and 1,176 in `7.mp4`.
- The selected extraction windows produced exactly the configured frame counts.
- The sleeve review clip decodes to 138 video frames; the blue-shirt review clip decodes to 84. Each is muted and displays every selected source frame once, at approximately one-quarter speed.
- All three annotated PNG boards were visually inspected for framing, image content, and readable labels.
- All five local image/video references in the HTML presentation resolve to actual files.
- All five media references in the standalone HTML export are embedded data URLs.
- Image links in both copies of `FINDINGS.md` resolve correctly.
- Generated output checksums were verified after the final presentation refresh.

The machine-readable result is in `VALIDATION.json`. Re-run these checks with `python scripts/validate.py`. The checks validate source and output integrity and packaging; they do not validate the interpretation of a gesture or establish authenticity of the recording.

## Rendering limit

A Chromium rendering check was attempted, but the browser binary was unavailable and its download failed. Desktop/mobile browser layout and native browser playback were therefore not directly tested. The HTML is self-contained or uses local assets, includes responsive CSS, and uses native video controls. Encoded video frames and HTML asset dependencies were checked independently.

## Build environment

- Python 3.12.14
- Pillow 12.3.0
- FFmpeg / ffprobe 6.1.1-3ubuntu5
- Linux x86-64

Full version strings are in `report/audit/environment.json`. The scripts are included so reviewers can repeat the build with their own tools and inspect any rendering differences. Source-byte hashes and frame indices remain the primary audit anchors across environments.
