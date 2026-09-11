# Study 01 · Method

Question, frozen before the frames were inspected (see `brief.md`): did two
men on the security line press something in the seconds before the shot, and
try to hide it?

## 1. Inputs and their integrity

Four files from the archive.org `kirkshooting` collection
(`inputs/README.md`). For each, `pipeline/s1_video.py timing` reads every
frame's presentation timestamp with ffprobe and reports the median, minimum
and maximum interval, any interval more than 1.5× the median, and near
duplicate frames (mean absolute difference below 0.15 grey levels between
consecutive decoded frames). Container tags are recorded as found.

Decisions taken from the result:

- `2.MOV` is a camera original (constant 16.67 ms intervals, no duplicates,
  iPhone tags). It is the clip used for every 60 fps claim. Only frames
  100–720 (1.7 s – 12.0 s) are extracted, which covers the shot with 4.7 s of
  margin before it; the 270 px copy `2.mp4` was used for orientation only.
- `16.mp4` is a variable-frame-rate re-encode (first frame held 204 ms). Its
  frame times are taken from the container, and its audio is not trusted to
  align with the video better than a few frames.
- `7.mp4` is an editor export at a constant 29.97 fps with no duplicated
  frames; its timing is used with the caveat that an export is not an
  original.

## 2. Time zero

`pipeline/s1_video.py audio` finds the loud transient in each clip: the 5 ms
RMS peak of the mono track, refined on a 1 ms envelope; the onset is the
first 1 ms window above 20 % of the peak envelope; later impulses are local
maxima above four times the 1 s pre-shot baseline. The transient's peak is
t = 0 for every figure. Kirk's first visible head movement is read from
per-frame crops and reported relative to it. A supersonic bullet's crack
arrives at a camera near the target roughly when the bullet does; the muzzle
report arrives later by (distance ÷ speed of sound − distance ÷ bullet
speed). Neither the camera positions nor the audio offsets are known well
enough to turn that into a distance; the second impulse in `7.mp4` is
reported, not interpreted.

## 3. Following each person

`track` is a normalised cross-correlation template tracker (OpenCV
`matchTemplate`, `TM_CCOEFF_NORMED`) seeded on a torso box in one frame,
searched within ±40–50 px per frame, with a slow template update (0.9/0.1)
that survives pose drift but resists jumping to another person. Every
trajectory is saved with its per-frame match score; frames with a score
below about 0.7 are treated as unreliable and the figures avoid them.

Tracked: the blue-shirt man in `7.mp4` (frames 240–830) and `16.mp4`
(0–250); the white-polo man in `7.mp4` (240–800) and `2.MOV` (179–700); the
plaid-shirt man at the barrier in `2.MOV` (179–700).

## 4. Stabilised film strips

`strip` cuts the same box, relative to the tracked position, out of every
frame in a window, magnifies it with bicubic interpolation (no sharpening,
no interpolation between frames) and labels it with the frame index and the
frame's timestamp relative to t = 0. Frames after Kirk is visibly wounded
are excluded from the published strips.

## 5. Motion inside a region

`motion` measures the mean absolute difference between consecutive
stabilised crops of a region of interest (the folded arms; the hand, phone
and ear; the forearms on the barrier) after a 5 px Gaussian blur, and the
same quantity for a control region on the same person (lower torso, cap,
chest) that should be still when the hands are. A hand movement shows as the
region rising above the control; a camera shake, zoom or whole-body turn
lifts both. The pre-shot median and 95th percentile of the region series are
the comparison for anything seen in the final second.

## 6. What was not done

- No blinded rating by independent reviewers.
- No other camera angle of the plaid-shirt man's hands.
- No native file for `16.mp4` or `7.mp4`.
- No estimate of what either man's hands were doing when out of view.

## Grading

Each claim is graded at three levels: observable movement, identifiable
action, purpose. The study can reach the first for every movement it
catalogues, reaches the second only where the object is resolved (a phone)
or where the hand is shown to be occluded (no action resolvable), and does
not address the third.
