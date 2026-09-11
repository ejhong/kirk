#!/usr/bin/env python3
"""Study 01 · frame-level analysis of the security-team gestures.

One script, several sub-commands. Every figure on docs/s1/index.html is
produced by `figures`, every number by `timing`, `audio` and `motion`.

    extract  pull every frame (PNG) and the audio track (WAV) out of a clip
    timing   per-frame timestamps: frame-rate constancy, duplicates, cuts
    audio    locate the loud transient, plot the waveform, look for a second impulse
    track    follow one person with normalised cross-correlation (a template tracker)
    strip    stabilised per-frame crops laid out as a film strip, labelled in ms
    motion   mean absolute frame-to-frame change inside a tracked region, plotted
    gridref  one gridded crop, used to choose region coordinates by eye
    figures  the whole manifest of strips, motion plots and orientation frames
    gifs     looping animations: stabilised subject, Kirk, and the audio timeline

Frame index i is zero-based; frame files are named f{i+1:05d}.png. Times are
the frame's presentation timestamp (PTS) from ffprobe, not i / fps, so the
variable-frame-rate copy (16.mp4) is labelled honestly.

Work directory: $KIRK_WORK or data/s1/work (frames, audio, timestamps; not
versioned). Results: data/s1 (JSON/CSV) and docs/s1/img (figures).
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("KIRK_WORK", ROOT / "data" / "s1" / "work"))
DATA = ROOT / "data" / "s1"
IMG = ROOT / "docs" / "s1" / "img"

# Clip registry. Keys are the short names used throughout; `file` is the
# archive.org file name (https://archive.org/download/kirkshooting/).
CLIPS = {
    "k1hq": {"file": "2.MOV", "label": "2.MOV", "fps": 60000 / 1001, "window": (100, 720)},
    "k1": {"file": "2.mp4", "label": "2.mp4", "fps": 2997 / 50},
    "k2": {"file": "16.mp4", "label": "16.mp4", "fps": 30.0},
    "k3": {"file": "7.mp4", "label": "7.mp4", "fps": 30000 / 1001},
}

# t = 0 reference per clip: the peak of the loud transient (seconds into the
# clip's audio track), as measured by `audio`. Kept here so that `strip`,
# `motion` and `figures` label frames consistently.
T0 = {"k1hq": 6.4189, "k1": 6.4189, "k2": 5.0370, "k3": 25.6980}

# Erebus palette (docs/style.css)
INK, INK_SOFT, LINE, STEEL, INDIGO, DOSSIER = "#121a24", "#3b4759", "#c2cfe0", "#3a6ea8", "#5c64a0", "#0d141d"


def clip_file(clip: str) -> Path:
    return ROOT / "inputs" / "kirkshooting" / CLIPS[clip]["file"]


def frames_dir(clip: str) -> Path:
    return WORK / f"frames_{clip}"


def frame_path(clip: str, i: int) -> Path:
    return frames_dir(clip) / f"f{i + 1:05d}.png"


def pts(clip: str) -> list[float]:
    p = WORK / f"pts_{clip}.csv"
    return [float(l.split(",")[0]) for l in p.read_text().splitlines() if l.strip()]


def t_rel(clip: str, i: int, P=None) -> float:
    """Seconds between the start of frame i and the clip's audio transient peak."""
    P = P or pts(clip)
    return P[i] - T0[clip]


# --------------------------------------------------------------------------- extract
def cmd_extract(a):
    import shutil

    c = CLIPS[a.clip]
    src = clip_file(a.clip)
    fd = frames_dir(a.clip)
    fd.mkdir(parents=True, exist_ok=True)
    (WORK / "audio").mkdir(parents=True, exist_ok=True)
    start, end = (a.start, a.end) if a.start is not None else c.get("window", (None, None))
    vf = []
    if start is not None:
        vf = ["-vf", f"select='between(n,{start},{end})'", "-start_number", str(start + 1)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-vsync", "passthrough", *vf,
                    str(fd / "f%05d.png")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-vn", "-ac", "1",
                    str(WORK / "audio" / f"{a.clip}.wav")], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout
    (WORK / f"pts_{a.clip}.csv").write_text(out)
    print(a.clip, "frames:", len(glob.glob(str(fd / "*.png"))), "pts rows:", len(out.splitlines()))


# --------------------------------------------------------------------------- timing
def cmd_timing(a):
    import cv2
    import numpy as np

    res = {}
    for clip, c in CLIPS.items():
        P = np.array(pts(clip))
        d = np.diff(P) * 1000
        probe = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size:format_tags=creation_time,com.apple.quicktime.model,com.apple.quicktime.software,com.apple.quicktime.location.ISO6709,com.apple.quicktime.creationdate"
             ":stream=codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,nb_frames,sample_rate",
             "-of", "json", str(clip_file(clip))], capture_output=True, text=True, check=True).stdout)
        v = [s for s in probe["streams"] if s["codec_type"] == "video"][0]
        au = [s for s in probe["streams"] if s["codec_type"] == "audio"][0]
        # duplicate / cut detection on decoded frames (windowed for the 1080p original)
        lo, hi = c.get("window", (0, len(P)))
        hi = min(hi, len(P))
        prev, diffs = None, []
        for i in range(lo, hi):
            im = cv2.imread(str(frame_path(clip, i)), cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            im = im.astype(np.float32)
            if prev is not None:
                diffs.append(float(np.abs(im - prev).mean()))
            prev = im
        diffs = np.array(diffs)
        dup = int((diffs < 0.15).sum())
        cuts = [int(lo + 1 + i) for i in np.argsort(diffs)[-5:][::-1]]
        res[clip] = {
            "file": c["file"], "codec": v["codec_name"], "width": v["width"], "height": v["height"],
            "r_frame_rate": v["r_frame_rate"], "avg_frame_rate": v["avg_frame_rate"], "nb_frames": int(v["nb_frames"]),
            "duration_s": float(probe["format"]["duration"]), "size_bytes": int(probe["format"]["size"]),
            "audio_codec": au["codec_name"], "audio_sample_rate": int(au["sample_rate"]),
            "tags": probe["format"].get("tags", {}),
            "pts_count": int(len(P)), "dt_ms_median": float(np.median(d)), "dt_ms_min": float(d.min()),
            "dt_ms_max": float(d.max()), "first_gap_ms": float(d[0]),
            "gaps_over_1p5x": [[int(i), float(round(d[i], 2))] for i in np.where(d > np.median(d) * 1.5)[0]][:20],
            "checked_frames": [lo, hi], "near_duplicate_frames": dup,
            "consecutive_diff_median": float(np.median(diffs)), "largest_diff_frames": cuts,
        }
        print(clip, {k: res[clip][k] for k in ("width", "height", "r_frame_rate", "avg_frame_rate", "nb_frames", "dt_ms_median", "dt_ms_min", "dt_ms_max", "near_duplicate_frames")})
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "timing.json").write_text(json.dumps(res, indent=2))


# --------------------------------------------------------------------------- audio
def cmd_audio(a):
    import numpy as np
    from scipy.io import wavfile
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    IMG.mkdir(parents=True, exist_ok=True)
    res = {}
    for clip in ("k1hq", "k1", "k2", "k3"):
        sr, x = wavfile.read(WORK / "audio" / f"{clip}.wav")
        x = x.astype(np.float32) / 32768
        win = int(sr * 0.005)
        n = len(x) // win
        env5 = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(1))
        t5 = np.arange(n) * win / sr
        pk = float(t5[env5.argmax()])
        # refine on a 1 ms envelope around the coarse peak
        seg0 = max(0, int((pk - 0.06) * sr))
        seg = x[seg0: int((pk + 0.7) * sr)]
        w = int(sr * 0.001)
        m = len(seg) // w
        e = np.sqrt((seg[: m * w].reshape(m, w) ** 2).mean(1))
        t = np.arange(m) * w / sr + seg0 / sr
        base = float(np.sqrt((x[int((pk - 1.05) * sr): int((pk - 0.1) * sr)] ** 2).mean()))
        peak_t, peak_v = float(t[e.argmax()]), float(e.max())
        onset = float(t[np.where(e > 0.2 * e.max())[0][0]])
        later = []
        for j in range(1, m - 1):
            if e[j] > e[j - 1] and e[j] >= e[j + 1] and e[j] > 4 * base and t[j] > peak_t + 0.06:
                if not later or t[j] - later[-1][0] > 0.04:
                    later.append((float(t[j]), float(e[j])))
        fps = CLIPS[clip]["fps"]
        P = pts(clip)
        frame_at = lambda s: int(max(i for i in range(len(P)) if P[i] <= s))
        res[clip] = {
            "sample_rate": int(sr), "baseline_rms_1s_before": base, "onset_s": onset, "peak_s": peak_t,
            "peak_rms_1ms": peak_v, "peak_over_baseline_db": float(20 * np.log10(peak_v / base)),
            "onset_frame": frame_at(onset), "peak_frame": frame_at(peak_t),
            "later_impulses": [{"t_after_peak_s": round(tt - peak_t, 4), "rms": round(vv, 4)} for tt, vv in later[:8]],
            "clip_abs_max_sample": float(np.abs(x).max()),
        }
        print(clip, {k: res[clip][k] for k in ("onset_s", "peak_s", "onset_frame", "peak_frame", "peak_over_baseline_db", "later_impulses")})
        # figure
        fig, ax = plt.subplots(2, 1, figsize=(10.5, 4.6), dpi=130, facecolor="white")
        ts = np.arange(len(seg)) / sr + seg0 / sr
        ax[0].plot(ts, seg, lw=0.35, color=STEEL)
        ax[0].set_ylabel("amplitude")
        ax[1].plot(t, 20 * np.log10(e / base + 1e-9), lw=0.8, color=INK)
        ax[1].set_ylabel("dB above 1 s baseline")
        ax[1].set_xlabel(f"seconds into {CLIPS[clip]['label']}")
        for k in range(len(P)):
            if ts[0] <= P[k] <= ts[-1]:
                for a_ in ax:
                    a_.axvline(P[k], color=LINE, lw=0.5, zorder=0)
        for a_ in ax:
            a_.axvline(onset, color=INDIGO, ls="--", lw=0.9)
            a_.set_xlim(ts[0], ts[-1])
            for s in ("top", "right"):
                a_.spines[s].set_visible(False)
        ax[0].set_title(f"{CLIPS[clip]['label']}: waveform and 1 ms envelope · frame boundaries in pale blue · onset dashed",
                        loc="left", fontsize=9.5, color=INK_SOFT)
        fig.tight_layout()
        fig.savefig(IMG / f"audio_{clip}.png")
        plt.close(fig)
    (DATA / "audio.json").write_text(json.dumps(res, indent=2))


# --------------------------------------------------------------------------- track
def track(clip, start, end, box, search):
    import cv2
    import numpy as np

    x0, y0, x1, y1 = box
    tw, th = x1 - x0, y1 - y0
    im = cv2.imread(str(frame_path(clip, start)))
    H, W = im.shape[:2]
    tpl = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    traj, cx, cy = {}, x0, y0
    step = 1 if end > start else -1
    for i in range(start, end, step):
        im = cv2.imread(str(frame_path(clip, i)))
        if im is None:
            break
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        sx0, sy0 = max(0, cx - search), max(0, cy - search)
        sx1, sy1 = min(W, cx + tw + search), min(H, cy + th + search)
        res = cv2.matchTemplate(g[sy0:sy1, sx0:sx1], tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        cx, cy = sx0 + loc[0], sy0 + loc[1]
        traj[i] = (int(cx), int(cy), float(mx))
        cur = g[cy: cy + th, cx: cx + tw].astype(np.float32)
        if cur.shape == tpl.shape:  # slow template update: survives pose drift, resists jumping
            tpl = cv2.addWeighted(tpl.astype(np.float32), 0.9, cur, 0.1, 0).astype(np.uint8)
    return traj


def cmd_track(a):
    traj = {}
    if a.back is not None:
        traj.update(track(a.clip, a.start, a.back, a.box, a.search))
    traj.update(track(a.clip, a.start, a.end, a.box, a.search))
    out = DATA / f"traj_{a.name}.json"
    out.write_text(json.dumps({"clip": a.clip, "seed_frame": a.start, "seed_box": a.box, "search": a.search,
                               "frames": {str(k): v for k, v in sorted(traj.items())}}))
    sc = [v[2] for v in traj.values()]
    print(a.name, "frames", min(traj), max(traj), "min score", round(min(sc), 3), "median", round(sorted(sc)[len(sc) // 2], 3))


def load_traj(name):
    d = json.loads((DATA / f"traj_{name}.json").read_text())
    return {int(k): v for k, v in d["frames"].items()}


# --------------------------------------------------------------------------- strip
def crop_rel(im, ox, oy, box):
    import numpy as np

    dx0, dy0, dx1, dy1 = box
    x0, y0, x1, y1 = ox + dx0, oy + dy0, ox + dx1, oy + dy1
    H, W = im.shape[:2]
    pad = np.zeros((dy1 - dy0, dx1 - dx0) + im.shape[2:], im.dtype)
    sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if sx1 > sx0 and sy1 > sy0:
        pad[sy0 - y0: sy1 - y0, sx0 - x0: sx1 - x0] = im[sy0:sy1, sx0:sx1]
    return pad


def strip(clip, traj, start, end, step, box, scale, cols, out, quality=88):
    import cv2
    import numpy as np

    T = load_traj(traj) if traj else None
    P = pts(clip)
    ims = []
    for i in range(start, end, step):
        im = cv2.imread(str(frame_path(clip, i)))
        if im is None or (T and i not in T):
            continue
        ox, oy = (T[i][0], T[i][1]) if T else (0, 0)
        c = crop_rel(im, ox, oy, box)
        c = cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        ms = t_rel(clip, i, P) * 1000
        bar = np.full((22, c.shape[1], 3), (29, 20, 13), np.uint8)  # dossier blue-black, BGR
        col = (160, 172, 216) if ms < 0 else (216, 172, 133)
        if P[i] <= T0[clip] < (P[i + 1] if i + 1 < len(P) else P[i] + 1 / CLIPS[clip]["fps"]):
            col = (60, 60, 230)  # the frame whose interval contains the transient peak
        cv2.putText(bar, f"{i}  {ms:+.0f} ms", (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.46, col, 1, cv2.LINE_AA)
        ims.append(np.vstack([bar, c]))
    rows = [np.hstack(ims[i: i + cols]) for i in range(0, len(ims), cols)]
    w = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0)), constant_values=13) for r in rows]
    sheet = np.vstack(rows)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, quality])
    else:
        cv2.imwrite(str(out), sheet)
    print(out.name, len(ims), "frames", sheet.shape[1], "x", sheet.shape[0])


def cmd_strip(a):
    strip(a.clip, a.traj, a.start, a.end, a.step, a.box, a.scale, a.cols, a.out)


# --------------------------------------------------------------------------- motion
def motion(clip, traj, start, end, region, control, name, title, xlim=None):
    import cv2
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    T = load_traj(traj)
    P = pts(clip)
    prev, rows = None, []
    for i in range(start, end):
        if i not in T:
            continue
        im = cv2.imread(str(frame_path(clip, i)), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        im = im.astype(np.float32)
        ox, oy = T[i][0], T[i][1]
        rc = cv2.GaussianBlur(crop_rel(im, ox, oy, region), (5, 5), 0)
        cc = cv2.GaussianBlur(crop_rel(im, ox, oy, control), (5, 5), 0)
        if prev is not None:
            rows.append((i, t_rel(clip, i, P), float(np.abs(rc - prev[0]).mean()), float(np.abs(cc - prev[1]).mean()), T[i][2]))
        prev = (rc, cc)
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / f"motion_{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_rel_s", "region_mean_abs_diff", "control_mean_abs_diff", "track_score"])
        w.writerows(rows)
    A = np.array(rows)
    t, hm, cm = A[:, 1], A[:, 2], A[:, 3]
    pre = hm[(t < -0.05)]
    last1 = hm[(t >= -1.0) & (t < 0)]
    summary = {
        "n": int(len(t)), "t_min": float(t[0]), "t_max": float(t[-1]),
        "region_median": float(np.median(hm)), "region_p90": float(np.percentile(hm, 90)), "region_max": float(hm.max()),
        "region_max_t": float(t[hm.argmax()]), "control_median": float(np.median(cm)),
        "pre_shot_median": float(np.median(pre)), "pre_shot_p95": float(np.percentile(pre, 95)),
        "last_second_max": float(last1.max()) if len(last1) else None,
        "last_second_max_percentile_of_pre": float((pre < last1.max()).mean() * 100) if len(last1) else None,
    }
    fig, ax = plt.subplots(figsize=(10.5, 3.3), dpi=130, facecolor="white")
    ax.fill_between(t, 0, cm, color=LINE, lw=0, label="control region")
    ax.plot(t, hm, color=STEEL, lw=1.0, label="region of interest")
    ax.axvline(0, color=INDIGO, ls="--", lw=1, label="audio transient peak")
    ax.set_xlabel("seconds relative to the audio transient")
    ax.set_ylabel("mean |Δ| between frames")
    ax.set_title(title, loc="left", fontsize=10, color=INK_SOFT)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_xlim(*(xlim or (t[0], t[-1])))
    ax.set_ylim(0, max(hm.max(), cm.max()) * 1.05)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / f"motion_{name}.png")
    plt.close(fig)
    print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summary.items()})
    return summary


def cmd_motion(a):
    s = motion(a.clip, a.traj, a.start, a.end, a.region, a.control, a.name, a.title)
    (DATA / f"motion_{a.name}.json").write_text(json.dumps(s, indent=2))


# --------------------------------------------------------------------------- gridref
def cmd_gridref(a):
    import cv2

    T = load_traj(a.traj) if a.traj else None
    ox, oy = (T[a.frame][0], T[a.frame][1]) if T else (0, 0)
    im = cv2.imread(str(frame_path(a.clip, a.frame)))
    c = crop_rel(im, ox, oy, a.box)
    c = cv2.resize(c, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_CUBIC)
    dx0, dy0, dx1, dy1 = a.box
    step = 20 if (dx1 - dx0) > 200 else 10
    for gx in range(dx0 - dx0 % step, dx1, step):
        X = int((gx - dx0) * a.scale)
        cv2.line(c, (X, 0), (X, c.shape[0]), (0, 0, 255) if gx == 0 else (255, 255, 0), 1)
        cv2.putText(c, str(gx), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1)
    for gy in range(dy0 - dy0 % step, dy1, step):
        Y = int((gy - dy0) * a.scale)
        cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if gy == 0 else (255, 255, 0), 1)
        cv2.putText(c, str(gy), (2, Y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1)
    cv2.imwrite(a.out, c)


# --------------------------------------------------------------------------- figures
TRACKS = [
    # name, clip, seed frame, seed box (x0 y0 x1 y1), search, forward end, backward end
    ("k3blue", "k3", 760, (985, 555, 1055, 665), 40, 830, 240),
    ("k3polo", "k3", 760, (1100, 540, 1150, 640), 40, 800, 240),
    ("k2blue", "k2", 0, (280, 515, 370, 665), 40, 250, None),
    ("k1tan", "k1hq", 385, (540, 640, 680, 800), 50, 700, 179),
    ("k1polo", "k1hq", 385, (0, 640, 160, 860), 50, 700, 179),
]

MOTION = [
    # name, clip, traj, start, end, region (rel. box), control (rel. box), title
    ("k3blue", "k3", "k3blue", 241, 790, (-5, 40, 60, 95), (0, 95, 55, 135),
     "Blue-shirt man · folded-arms region vs lower torso · 7.mp4 (1080p, 29.97 fps)"),
    ("k2blue", "k2", "k2blue", 0, 205, (0, 50, 62, 100), (10, 100, 60, 128),
     "Blue-shirt man · folded-arms region vs lower torso · 16.mp4 (720p, 30 fps)"),
    ("k1polo", "k1hq", "k1polo", 200, 640, (100, 60, 330, 460), (0, 0, 120, 180),
     "White-polo man · hand / phone / ear region vs cap · 2.MOV (1080p, 59.94 fps)"),
    ("k1tan", "k1hq", "k1tan", 200, 640, (-40, 100, 200, 220), (100, 30, 200, 100),
     "Plaid-shirt man · forearms-on-barrier region vs chest · 2.MOV (1080p, 59.94 fps)"),
    ("k1tan_sleeve", "k1hq", "k1tan", 200, 640, (70, 20, 200, 120), (0, -50, 70, -5),
     "Plaid-shirt man · left sleeve and upper chest vs a neighbour's cap · 2.MOV (1080p, 59.94 fps)"),
]

STRIPS = [
    # out, clip, traj, start, end, step, box (rel.), scale, cols
    ("k1polo_ear.jpg", "k1hq", "k1polo", 212, 264, 2, (60, 40, 330, 460), 0.62, 13),
    ("k1polo_shot.jpg", "k1hq", "k1polo", 300, 440, 4, (-20, -40, 330, 460), 0.5, 12),
    ("k3polo_shot.jpg", "k3", "k3polo", 680, 772, 4, (-40, -40, 90, 150), 2.2, 12),
    ("k1tan_shot.jpg", "k1hq", "k1tan", 340, 430, 2, (-20, -80, 320, 240), 0.8, 9),
    ("k1tan_hands.jpg", "k1hq", "k1tan", 200, 400, 4, (-20, -80, 320, 240), 0.8, 10),
    ("k1tan_sleeve.jpg", "k1hq", "k1tan", 466, 572, 2, (-20, -80, 320, 240), 1.0, 9),
    ("k1tan_sleeve_zoom.jpg", "k1hq", "k1tan", 484, 520, 1, (120, -50, 310, 170), 2.2, 9),
    ("k1_kirk_state.jpg", "k1hq", None, 370, 580, 10, (0, 300, 1080, 1300), 0.36, 11),
    ("k2_kirk_state.jpg", "k2", None, 140, 218, 3, (150, 400, 700, 760), 0.9, 9),
    ("k2blue_after.jpg", "k2", "k2blue", 150, 216, 2, (-30, -25, 140, 175), 2.0, 11),
    ("k3blue_fist.jpg", "k3", "k3blue", 776, 812, 2, (-10, -10, 60, 100), 5.0, 9),
    ("k3blue_shot.jpg", "k3", "k3blue", 745, 777, 1, (-10, -20, 80, 120), 3.0, 8),
    ("k3blue_turn.jpg", "k3", "k3blue", 664, 700, 2, (-10, -20, 80, 120), 2.4, 9),
    ("k3blue_baseline.jpg", "k3", "k3blue", 241, 745, 8, (-40, -60, 110, 150), 1.6, 12),
    ("k3blue_after.jpg", "k3", "k3blue", 770, 812, 2, (-70, -40, 70, 200), 1.6, 11),
    ("k3blue_unfold.jpg", "k3", "k3blue", 766, 780, 1, (-15, 25, 60, 110), 5.0, 7),
    ("k2blue_shot.jpg", "k2", "k2blue", 130, 175, 1, (-10, -10, 100, 150), 3.0, 9),
    ("k2blue_baseline.jpg", "k2", "k2blue", 0, 206, 4, (-30, -25, 110, 165), 2.0, 13),
    ("k1_reaction.jpg", "k1hq", None, 379, 392, 1, (100, 640, 500, 1040), 0.6, 13),
    ("k2_reaction.jpg", "k2", None, 146, 156, 1, (430, 520, 560, 660), 2.5, 10),
    ("k3_reaction.jpg", "k3", None, 764, 775, 1, (1000, 540, 1130, 700), 2.2, 11),
]


def cmd_figures(a):
    import cv2

    IMG.mkdir(parents=True, exist_ok=True)
    if a.track:
        for name, clip, seed, box, search, fwd, back in TRACKS:
            traj = {}
            if back is not None:
                traj.update(track(clip, seed, back, box, search))
            traj.update(track(clip, seed, fwd, box, search))
            (DATA / f"traj_{name}.json").write_text(json.dumps(
                {"clip": clip, "seed_frame": seed, "seed_box": box, "search": search,
                 "frames": {str(k): v for k, v in sorted(traj.items())}}))
            sc = [v[2] for v in traj.values()]
            print("tracked", name, min(traj), max(traj), "min score", round(min(sc), 3))
    summaries = {}
    for name, clip, traj, start, end, region, control, title in MOTION:
        summaries[name] = motion(clip, traj, start, end, region, control, name, title)
    (DATA / "motion_summary.json").write_text(json.dumps(summaries, indent=2))
    for out, clip, traj, start, end, step, box, scale, cols in STRIPS:
        strip(clip, traj, start, end, step, box, scale, cols, IMG / out)
    audio_context()
    # orientation frames: a crop of the tent with the subjects boxed and labelled
    for out, clip, frame, crop, scale, boxes in ORIENT:
        im = cv2.imread(str(frame_path(clip, frame)))
        cx0, cy0, cx1, cy1 = crop
        im = im[cy0:cy1, cx0:cx1]
        im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
        for lab, (x0, y0, x1, y1), (lx, ly) in boxes:
            X0, Y0, X1, Y1 = [int((v - o) * scale) for v, o in ((x0, cx0), (y0, cy0), (x1, cx0), (y1, cy0))]
            LX, LY = int((lx - cx0) * scale), int((ly - cy0) * scale)
            cv2.rectangle(im, (X0, Y0), (X1, Y1), (216, 172, 133), 2)
            (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(im, (LX - 4, LY - th - 8), (LX + tw + 4, LY + 4), (29, 20, 13), -1)
            cv2.putText(im, lab, (LX, LY), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (216, 172, 133), 1, cv2.LINE_AA)
            ax, ay = (X0 + X1) // 2, Y0 if LY < Y0 else Y1
            cv2.line(im, (LX + tw // 2, LY + 4 if LY < Y0 else LY - th - 8), (ax, ay), (216, 172, 133), 1, cv2.LINE_AA)
        cv2.imwrite(str(IMG / out), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(out, im.shape[1], "x", im.shape[0])


def audio_context():
    """2.MOV, 5.5-9.5 s: the transient, Kirk's reaction, the crowd, and the sleeve touch on one time axis."""
    import numpy as np
    from scipy.io import wavfile
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sr, x = wavfile.read(WORK / "audio" / "k1hq.wav")
    x = x.astype(np.float32) / 32768
    lo, hi = 5.5, 9.5
    seg = x[int(lo * sr): int(hi * sr)]
    w = int(sr * 0.002)
    m = len(seg) // w
    e = np.sqrt((seg[: m * w].reshape(m, w) ** 2).mean(1))
    t = np.arange(m) * w / sr + lo
    P = pts("k1hq")
    fig, ax = plt.subplots(figsize=(10.5, 3.4), dpi=130, facecolor="white")
    ax.fill_between(t, 0, e, color=STEEL, lw=0)
    marks = [(T0["k1hq"], "audio transient\n6.42 s · frame 385", INDIGO), (P[390], "Kirk's microphone\nhand drops · frame 390", INK),
             (P[440], "crowd begins\nto react · ~frame 440", INK_SOFT), (P[490], "plaid man's right hand\nrises · frame 490", "#8a4b3a"),
             (P[496], "hand on the left\nsleeve · frame 496", "#8a4b3a")]
    for i, (tt, lab, col) in enumerate(marks):
        ax.axvline(tt, color=col, ls="--" if i == 0 else ":", lw=1)
        ax.text(tt + 0.03, e.max() * (0.95 - 0.16 * (i % 3)), lab, fontsize=7.5, color=col, va="top")
    ax.set_xlim(lo, hi)
    ax.set_ylim(0, e.max() * 1.05)
    ax.set_xlabel("seconds into 2.MOV")
    ax.set_ylabel("2 ms RMS")
    ax.set_title("2.MOV: the transient, Kirk's reaction, the crowd, and the sleeve touch on one time axis", loc="left", fontsize=10, color=INK_SOFT)
    for sp_ in ("top", "right"):
        ax.spines[sp_].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "audio_context_k1hq.png")
    plt.close(fig)


ORIENT = [
    # out, clip, frame, crop (x0 y0 x1 y1), scale, [(label, box, label anchor)]
    ("orient_k1.jpg", "k1hq", 385, (0, 380, 1080, 1180), 0.85, [
        ("A2 · white polo, phone at left shoulder", (0, 560, 300, 1180), (20, 1160)),
        ("A · plaid shirt, both hands on the barrier", (560, 580, 830, 870), (470, 905)),
        ("Kirk", (150, 420, 520, 1100), (330, 410)),
    ]),
    ("orient_k3.jpg", "k3", 760, (860, 430, 1360, 780), 2.0, [
        ("B · blue shirt, arms folded", (975, 535, 1065, 700), (880, 520)),
        ("A2 · white polo", (1095, 520, 1160, 660), (1140, 500)),
        ("Kirk", (1010, 560, 1130, 720), (1060, 750)),
    ]),
    ("orient_k2.jpg", "k2", 150, (100, 330, 620, 700), 2.0, [
        ("B · blue shirt, arms folded", (270, 500, 380, 680), (140, 490)),
        ("Kirk", (440, 530, 560, 660), (470, 690)),
    ]),
]



# --------------------------------------------------------------------------- gifs
FONT_CANDIDATES = [ROOT / "pipeline" / "assets" / "DejaVuSans.ttf", Path("/System/Library/Fonts/Supplemental/Arial.ttf")]

GIFS = [
    # out, clip, traj, start, end, step, subject box (rel.), subject label, kirk box (abs), kirk blackout frame or None,
    # playback fps, phases [(frame, caption)]
    ("k1tan.gif", "k1hq", "k1tan", 330, 580, 3, (-30, -80, 320, 240), "A · plaid shirt, stabilised",
     (120, 400, 520, 900), None, 10, [
         (330, "forearms crossed on the barrier"), (385, "audio transient · Kirk's microphone drops"),
         (430, "arms unchanged, watching Kirk"), (490, "right hand rises to the left upper arm"),
         (498, "hand on the left sleeve; fingers reposition")]),
    ("k1polo.gif", "k1hq", "k1polo", 200, 440, 3, (-20, -40, 330, 460), "A2 · white polo, stabilised",
     (120, 400, 520, 900), None, 10, [
         (200, "phone held at the right ear"), (217, "fingers to the right ear"), (251, "phone taken from the ear"),
         (270, "phone held at the left shoulder"), (385, "audio transient · Kirk's microphone drops"),
         (400, "phone still at the shoulder")]),
    ("k3blue.gif", "k3", "k3blue", 730, 812, 1, (-10, -20, 80, 120), "B · blue shirt, stabilised",
     (1000, 540, 1130, 700), 778, 8, [
         (730, "arms folded, right hand under the left arm"), (770, "audio transient · Kirk's head jerks"),
         (777, "right hand emerges, rises to the chin"), (790, "turns toward Kirk")]),
    ("k2blue.gif", "k2", "k2blue", 120, 216, 1, (-30, -25, 140, 175), "B · blue shirt, stabilised",
     (430, 520, 560, 660), None, 8, [
         (120, "arms folded, seen from behind"), (145, "audio transient"), (151, "Kirk's head jerks back"),
         (198, "turns and unfolds; hands go down"), (206, "steps toward Kirk")]),
]


def _font(size):
    from PIL import ImageFont
    for f in FONT_CANDIDATES:
        if f.exists():
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default()


def gif(out, clip, traj, start, end, step, sbox, slabel, kbox, kblack, fps_play, phases):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy.io import wavfile
    import tempfile

    T = load_traj(traj)
    P = pts(clip)
    sr, x = wavfile.read(WORK / "audio" / f"{clip}.wav")
    x = x.astype(np.float32) / 32768
    t_lo, t_hi = t_rel(clip, start, P) - 0.05, t_rel(clip, end - 1, P) + 0.05
    # 2 ms RMS envelope over the window
    w = int(sr * 0.002)
    i0, i1 = max(0, int((t_lo + T0[clip]) * sr)), min(len(x), int((t_hi + T0[clip]) * sr))
    seg = x[i0:i1]
    m = len(seg) // w
    env = np.sqrt((seg[: m * w].reshape(m, w) ** 2).mean(1))
    tenv = np.arange(m) * w / sr + i0 / sr - T0[clip]
    env = env / max(env.max(), 1e-6)

    H = 300
    ink, paper, steel, indigo, amber, faint, white = (13, 20, 29), (233, 239, 247), (58, 110, 168), (92, 100, 160), (216, 172, 133), (128, 147, 171), (219, 229, 241)
    f_big, f_mid, f_small = _font(26), _font(15), _font(12)
    frames = []
    for i in range(start, end, step):
        if i not in T:
            continue
        im = cv2.imread(str(frame_path(clip, i)))
        if im is None:
            continue
        ox, oy = T[i][0], T[i][1]
        sub = crop_rel(im, ox, oy, sbox)
        sub = cv2.resize(sub, (int(sub.shape[1] * H / sub.shape[0]), H), interpolation=cv2.INTER_CUBIC)
        kx0, ky0, kx1, ky1 = kbox
        kirk = im[ky0:ky1, kx0:kx1]
        kirk = cv2.resize(kirk, (int(kirk.shape[1] * H / kirk.shape[0]), H), interpolation=cv2.INTER_AREA if kirk.shape[0] > H else cv2.INTER_CUBIC)
        withheld = kblack is not None and i >= kblack
        if withheld:
            kirk = np.full_like(kirk, 30)
        ms = t_rel(clip, i, P) * 1000
        gap, top, bottom = 10, 44, 150
        W = sub.shape[1] + gap + kirk.shape[1]
        canvas = Image.new("RGB", (W, top + H + bottom), ink)
        canvas.paste(Image.fromarray(cv2.cvtColor(sub, cv2.COLOR_BGR2RGB)), (0, top))
        canvas.paste(Image.fromarray(cv2.cvtColor(kirk, cv2.COLOR_BGR2RGB)), (sub.shape[1] + gap, top))
        d = ImageDraw.Draw(canvas)
        # header
        d.text((10, 8), f"{CLIPS[clip]['label']} · frame {i}", font=f_mid, fill=faint)
        tcol = amber if abs(ms) < 1000 / CLIPS[clip]["fps"] * step else (white if ms >= 0 else (160, 172, 216))
        d.text((W // 2, 6), f"{ms:+.0f} ms", font=f_big, fill=tcol, anchor="mt")
        # panel labels
        d.rectangle((0, top + H - 24, sub.shape[1], top + H), fill=(13, 20, 29))
        d.text((8, top + H - 20), slabel, font=f_small, fill=faint)
        d.rectangle((sub.shape[1] + gap, top + H - 24, W, top + H), fill=(13, 20, 29))
        d.text((sub.shape[1] + gap + 8, top + H - 20), "Kirk" + (" · frames after the wound are withheld" if withheld else ""), font=f_small, fill=faint)
        # phase caption
        cap = ""
        for fr, text in phases:
            if i >= fr:
                cap = text
        d.text((10, top + H + 8), cap, font=f_mid, fill=white)
        # timeline
        ty0, ty1 = top + H + 36, top + H + bottom - 26
        d.rectangle((0, ty0, W, ty1), fill=(20, 29, 42))
        xs = ((tenv - t_lo) / (t_hi - t_lo) * (W - 1)).astype(int)
        pts_poly = [(0, ty1)] + [(int(xx), int(ty1 - e * (ty1 - ty0 - 6))) for xx, e in zip(xs, env)] + [(W - 1, ty1)]
        d.polygon(pts_poly, fill=steel)
        x0 = int((0 - t_lo) / (t_hi - t_lo) * (W - 1))
        d.line((x0, ty0, x0, ty1), fill=indigo, width=2)
        d.text((x0 + 4, ty0 + 2), "transient", font=f_small, fill=(160, 172, 216))
        for tick in np.arange(np.ceil(t_lo * 2) / 2, t_hi, 0.5):
            xt = int((tick - t_lo) / (t_hi - t_lo) * (W - 1))
            d.line((xt, ty1, xt, ty1 + 5), fill=faint)
            d.text((xt, ty1 + 7), f"{tick:+.1f} s", font=f_small, fill=faint, anchor="mt")
        xc = int((ms / 1000 - t_lo) / (t_hi - t_lo) * (W - 1))
        d.line((xc, ty0 - 4, xc, ty1 + 4), fill=amber, width=3)
        arr = np.array(canvas)
        hold = 6 if abs(ms) < 1000 / CLIPS[clip]["fps"] * step else 1
        frames.extend([arr] * hold)
    frames.extend([frames[-1]] * 8)
    tmp = Path(tempfile.mkdtemp())
    for k, fr in enumerate(frames):
        Image.fromarray(fr).save(tmp / f"g{k:04d}.png")
    out = Path(out)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps_play), "-i", str(tmp / "g%04d.png"),
                    "-vf", "split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                    "-loop", "0", str(out)], check=True)
    # the same frames as a silent H.264 loop, which browsers play like a GIF at a fraction of the size
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps_play), "-i", str(tmp / "g%04d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-preset", "slow",
                    "-movflags", "+faststart", str(out.with_suffix(".mp4"))], check=True)
    for f in tmp.glob("*.png"):
        f.unlink()
    tmp.rmdir()
    print(out.name, len(frames), "frames", f"gif {out.stat().st_size / 1e6:.1f} MB", f"mp4 {out.with_suffix('.mp4').stat().st_size / 1e6:.2f} MB")


def cmd_gifs(a):
    IMG.mkdir(parents=True, exist_ok=True)
    for spec in GIFS:
        if a.only and spec[0] != a.only:
            continue
        gif(IMG / spec[0], *spec[1:])


# --------------------------------------------------------------------------- main
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("extract"); s.add_argument("--clip", required=True, choices=CLIPS); s.add_argument("--start", type=int); s.add_argument("--end", type=int); s.set_defaults(f=cmd_extract)
    s = sp.add_parser("timing"); s.set_defaults(f=cmd_timing)
    s = sp.add_parser("audio"); s.set_defaults(f=cmd_audio)
    s = sp.add_parser("track"); s.add_argument("--clip", required=True, choices=CLIPS); s.add_argument("--start", type=int, required=True); s.add_argument("--end", type=int, required=True); s.add_argument("--back", type=int); s.add_argument("--box", type=int, nargs=4, required=True); s.add_argument("--search", type=int, default=40); s.add_argument("--name", required=True); s.set_defaults(f=cmd_track)
    s = sp.add_parser("strip"); s.add_argument("--clip", required=True, choices=CLIPS); s.add_argument("--traj"); s.add_argument("--start", type=int, required=True); s.add_argument("--end", type=int, required=True); s.add_argument("--step", type=int, default=1); s.add_argument("--box", type=int, nargs=4, required=True); s.add_argument("--scale", type=float, default=1.0); s.add_argument("--cols", type=int, default=10); s.add_argument("--out", required=True); s.set_defaults(f=cmd_strip)
    s = sp.add_parser("motion"); s.add_argument("--clip", required=True, choices=CLIPS); s.add_argument("--traj", required=True); s.add_argument("--start", type=int, required=True); s.add_argument("--end", type=int, required=True); s.add_argument("--region", type=int, nargs=4, required=True); s.add_argument("--control", type=int, nargs=4, required=True); s.add_argument("--name", required=True); s.add_argument("--title", default=""); s.set_defaults(f=cmd_motion)
    s = sp.add_parser("gridref"); s.add_argument("--clip", required=True, choices=CLIPS); s.add_argument("--traj"); s.add_argument("--frame", type=int, required=True); s.add_argument("--box", type=int, nargs=4, required=True); s.add_argument("--scale", type=float, default=3.0); s.add_argument("--out", required=True); s.set_defaults(f=cmd_gridref)
    s = sp.add_parser("figures"); s.add_argument("--track", action="store_true", help="re-run the template trackers first"); s.set_defaults(f=cmd_figures)
    s = sp.add_parser("gifs"); s.add_argument("--only"); s.set_defaults(f=cmd_gifs)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
