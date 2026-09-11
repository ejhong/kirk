#!/usr/bin/env python3
"""Rebuild review aids from hash-verified sources and explicit manual annotations."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, base64, csv, hashlib, json, platform, re, shutil, subprocess, sys
import urllib.request
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[1]
BG, FG, MUTED, GOLD = '#14202b', '#f5f6f8', '#c0cbd6', '#efc57c'

def read(path):
    return json.loads(path.read_text())

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def verify(source, path):
    if not path.exists():
        raise FileNotFoundError(f'Missing {path}. Run fetch for archive sources; supplied copies are in the release ZIP.')
    if path.stat().st_size != source['bytes'] or sha(path) != source['sha256']:
        raise ValueError(f'Source mismatch: {path}. No analysis was run on replacement bytes.')

def fetch(sources, input_dir):
    for source in sources:
        path = input_dir / source['path']
        if path.exists():
            verify(source, path)
            continue
        if not source['url']:
            raise FileNotFoundError(f'Supplied source required: {path}')
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.part')
        print('Downloading', source['filename'], flush=True)
        request = urllib.request.Request(source['url'], headers={'User-Agent': 'KirkVideoReview/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, temp.open('wb') as out:
                shutil.copyfileobj(response, out)
            verify(source, temp)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)

def probe(source, input_dir, out):
    path = input_dir / source['path']
    verify(source, path)
    meta = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]))
    # Do not publish machine-dependent absolute paths in the source metadata.
    meta['format']['filename'] = source['path']
    raw = json.loads(run(['ffprobe', '-v', 'error', '-threads', '1', '-select_streams', 'v:0',
        '-show_frames', '-show_entries',
        'frame=best_effort_timestamp_time,pkt_duration_time,key_frame,pict_type', '-of', 'json', str(path)]))['frames']
    keys = ['best_effort_timestamp_time', 'pkt_duration_time', 'key_frame', 'pict_type']
    frames = [{k: f[k] for k in keys if k in f} for f in raw]
    times = [float(f['best_effort_timestamp_time']) for f in frames]
    intervals = [b-a for a,b in zip(times, times[1:])]
    audit = out / 'audit'
    dump(audit / (source['id'] + '_metadata.json'), meta)
    dump(audit / (source['id'] + '_frames.json'), frames)
    with (audit / (source['id'] + '_timestamps.csv')).open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['frame_zero_based', 'presentation_seconds', 'interval_from_previous_seconds', 'picture_type', 'key_frame'])
        for i, (f, t) in enumerate(zip(frames, times)):
            writer.writerow([i, f['best_effort_timestamp_time'], '' if i == 0 else f'{t-times[i-1]:.9f}', f.get('pict_type'), f.get('key_frame')])
    print('Verified and probed', source['filename'], len(frames), 'frames', flush=True)
    return source['id'], {'frames': frames, 'metadata': meta, 'summary': {
        'source': source['id'], 'sha256': source['sha256'], 'decoded_frames': len(frames),
        'min_pts_interval_seconds': min(intervals), 'max_pts_interval_seconds': max(intervals),
        'nonpositive_intervals': sum(x <= 0 for x in intervals)}}

def font(size):
    return ImageFont.truetype(str(ROOT / 'assets/DejaVuSans.ttf'), size)

def fitted(image, width, height):
    scale = min(width / image.width, height / image.height)
    return image.resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.NEAREST)

def extract(view, source, input_dir, cache):
    folder = cache / view['id']
    folder.mkdir(parents=True, exist_ok=True)
    # Remove only the generated PNGs for this configured view.
    for path in folder.glob('frame_*.png'):
        path.unlink()
    x,y,w,h = view['crop']
    lo,hi = view['start_frame'],view['end_frame']
    vf = f"select='between(n,{lo},{hi})',crop={w}:{h}:{x}:{y}"
    run(['ffmpeg', '-v', 'error', '-threads', '1', '-i', str(input_dir / source['path']),
         '-vf', vf, '-fps_mode', 'passthrough', '-y', str(folder / 'frame_%05d.png')])
    files = sorted(folder.glob('frame_*.png'))
    if len(files) != hi-lo+1:
        raise ValueError(f"{view['id']}: extracted {len(files)} frames; expected {hi-lo+1}")
    return {i: path for i,path in enumerate(files, lo)}

def panel(view, frame, image, pts):
    out = Image.new('RGB', (600,820), BG)
    draw = ImageDraw.Draw(out)
    draw.text((22,20), view['id'] + ' | 4x slower | muted', font=font(25), fill=FG)
    draw.text((22,62), f'Frame {frame} | file time {pts:.3f} s', font=font(23), fill=FG)
    draw.text((22,101), f"{pts-view['marker_seconds']:+.2f} s vs. approximate visual reference", font=font(19), fill=GOLD)
    im = fitted(image,560,595)
    out.paste(im, ((600-im.width)//2,145))
    draw.text((22,755), 'Decoded crop; no generated intermediate frames.', font=font(18), fill=MUTED)
    draw.text((22,786), 'File position does not establish exact firing time.', font=font(18), fill=MUTED)
    return out

def render(view, paths, frames, out):
    assets = out / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    indices = view['selected_frames']
    columns = 4 if len(indices) == 8 else 3
    cw,ch = 410,530
    board = Image.new('RGB', (cw*columns, 145+ch*2+75), BG)
    draw = ImageDraw.Draw(board)
    draw.text((22,19), view['title'], font=font(30), fill=FG)
    draw.text((22,65), view['finding'], font=font(21), fill=GOLD)
    draw.text((22,103), 'Decoded crops. Enlargement uses nearest-neighbor pixels. Frame indices start at zero.', font=font(17), fill=MUTED)
    for j,(i,label) in enumerate(zip(indices, view['labels'])):
        pts = float(frames[i]['best_effort_timestamp_time'])
        image = Image.open(paths[i]).convert('RGB')
        image.save(assets / f"{view['id']}_{i:04d}.png")
        x,y = j%columns*cw,145+j//columns*ch
        draw.text((x+14,y+6), f'Frame {i} | file {pts:.3f} s', font=font(19), fill=FG)
        draw.text((x+14,y+36), f"{pts-view['marker_seconds']:+.2f} s vs. visual reference", font=font(18), fill=GOLD)
        im = fitted(image,cw-24,ch-115)
        board.paste(im,(x+(cw-im.width)//2,y+74))
        draw.text((x+14,y+ch-28),label,font=font(18),fill=FG)
    draw.text((22,145+ch*2+10), 'Reference: first abrupt visible movement of Kirk; approximate, not the exact firing instant.',font=font(17),fill=MUTED)
    draw.text((22,145+ch*2+37), 'Hand occlusion and unresolved detail limit interpretation. See the accompanying assessment.',font=font(17),fill=MUTED)
    board.save(assets / (view['id'] + '_annotated.png'))
    if view['video']:
        video = assets / (view['id'] + '_slow_review.mp4')
        cmd = ['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','600x820',
               '-r',str(view['fps']/4),'-i','pipe:0','-an','-c:v','libx264','-threads','1',
               '-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
        proc = subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for i,path in paths.items():
                pts = float(frames[i]['best_effort_timestamp_time'])
                proc.stdin.write(panel(view,i,Image.open(path).convert('RGB'),pts).tobytes())
            proc.stdin.close()
            err = proc.stderr.read().decode()
            if proc.wait(): raise RuntimeError(err)
        except BaseException:
            proc.kill()
            proc.wait()
            raise

def html_report(out):
    (out / 'FINDINGS.md').write_text((ROOT / 'FINDINGS.md').read_text().replace('(report/assets/', '(assets/'))
    template = (ROOT / 'assets/report-template.html').read_text()
    (out / 'index.html').write_text(template)
    # Standalone export embeds the same review assets. No network is required to read it.
    def embed(match):
        rel = match.group(1)
        path = out / rel
        mime = 'image/png' if path.suffix == '.png' else 'video/mp4'
        return 'src="data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode() + '"'
    standalone = re.sub(r'src="(assets/[^\"]+)"', embed, template)
    (out / 'Kirk_video_review.html').write_text(standalone)

def checksums(out):
    checks = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'output_sha256.json'}
    dump(out / 'audit/output_sha256.json', checks)

def build(sources, input_dir, out, cache):
    annotations = read(ROOT / 'config/annotations.json')
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(lambda s: probe(s,input_dir,out), sources))
    by_id = {s['id']:s for s in sources}
    for view in annotations['views']:
        paths = extract(view,by_id[view['source']],input_dir,cache)
        render(view,paths,results[view['source']]['frames'],out)
        print('Rendered',view['id'],flush=True)
    dump(out / 'audit/source_checks.json', [r['summary'] for r in results.values()])
    dump(out / 'audit/annotations.json', annotations)
    dump(out / 'audit/environment.json', {'python':sys.version,'platform':platform.platform(),
        'pillow':pillow_version,'ffmpeg':run(['ffmpeg','-version']).splitlines()[0],
        'ffprobe':run(['ffprobe','-version']).splitlines()[0]})
    html_report(out)
    checksums(out)
    print('Review build complete:',out,flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['verify','fetch','build','all','present'])
    parser.add_argument('--input-dir',type=Path,default=ROOT/'inputs')
    parser.add_argument('--out',type=Path,default=ROOT/'report')
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache')
    args=parser.parse_args()
    sources=read(ROOT/'config/sources.json')['sources']
    if args.command in ['fetch','all']: fetch(sources,args.input_dir)
    if args.command == 'verify':
        for source in sources:
            verify(source,args.input_dir/source['path'])
            print('SHA-256 OK:',source['filename'])
    if args.command in ['build','all']: build(sources,args.input_dir,args.out,args.cache)
    if args.command == 'present':
        html_report(args.out)
        checksums(args.out)

if __name__ == '__main__':
    main()
