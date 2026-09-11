# Kirk Case Studies

Frame-level tests of claims made about the killing of Charlie Kirk at Utah
Valley University on 10 September 2025. Each study keeps its question,
finding and limitations together and grades what the footage supports, never
anyone's guilt.

[Public site](https://ejhong.github.io/kirk/) ·
[Erebus case file](https://ejhong.github.io/erebus/cases/kirk-assassination/) ·
[Research conventions](research/)

## Find your way around

| Study | Reading page | Research and reproducibility |
| --- | --- | --- |
| 01 · Two gestures before the shot | [Study page](docs/s1/index.html) | `pipeline/s1_video.py`, `data/s1/`, `inputs/kirkshooting/`; [brief](research/s1/brief.md), [method](research/s1/method.md) |
| 02 · Movement and timing: a second review | [Study page](docs/s2/index.html) | An independent review reproduced with an editor's note; its package in `research/s2/astra-package/`, original deliverable in `inputs/astra/` |

The [homepage](docs/index.html) lists the studies and the rules they follow.
`research/investigations.json` holds each study's question, finding and
limitations in one place.

## Work on the site

The site is static HTML and CSS; reading it needs nothing. Reproducing a
study needs ffmpeg, Python 3.11+ and the packages in `requirements.txt`.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
inputs/fetch.sh                                   # ~120 MB from archive.org, verified against SHA256SUMS
P=.venv/bin/python
for c in k1hq k1 k2 k3; do $P pipeline/s1_video.py extract --clip $c; done   # frames + audio + timestamps into data/s1/work
$P pipeline/s1_video.py timing                    # data/s1/timing.json
$P pipeline/s1_video.py audio                     # data/s1/audio.json: impulses around the anchor
$P pipeline/s1_video.py sync                      # data/s1/sync.json: cross-clip lags vs the video anchors
$P pipeline/s1_video.py figures --track           # trajectories, motion series and every strip on the study page
$P pipeline/s1_video.py gifs                      # the looping animations (subject · Kirk · audio timeline)
python3 -m http.server 4173 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:4173/`. Extracting `2.MOV` at 1080p writes about
5.5 GB of PNG frames for the 620-frame window the study uses; set
`KIRK_WORK` to put the work directory elsewhere.

## Repository layout

```text
inputs/                       Original supplied material; preserve untouched
  README.md                   Provenance of each clip and what its container says
  fetch.sh, kirkshooting/     Download script and SHA-256 checksums (the videos are not committed)
pipeline/s1_video.py          extract · timing · audio · sync · track · strip · motion · gridref · figures · gifs
pipeline/assets/              DejaVu Sans for the animation labels, with its licence
data/s1/                      timing.json, audio.json, traj_*.json, motion_*.csv, motion_summary.json
research/                     investigations.json, per-study brief and method; s2/astra-package is study 02 as delivered
docs/                         The site: index.html, style.css, s1/ and s2/ with their figures
```

## Conventions

- People in the frames are described by clothing and position only.
- Times are frame presentation timestamps from the file, relative to the
  frame in which Kirk visibly moves in that same clip. Frame indices are zero-based.
- Frames after Kirk is visibly wounded are not published.
- Every figure on the site is produced by the pipeline from the listed
  inputs; nothing is drawn by hand.
