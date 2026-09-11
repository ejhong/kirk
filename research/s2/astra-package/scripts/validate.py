#!/usr/bin/env python3
"""Validate source hashes, rendered frame counts, and packaged report dependencies."""
from pathlib import Path
from html.parser import HTMLParser
import argparse, hashlib, json, re, subprocess
from review import ROOT, read, sha, verify

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'src' in attrs:self.sources.append(attrs['src'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'report')
    parser.add_argument('--input-dir',type=Path,default=ROOT/'inputs')
    args=parser.parse_args();out=args.out
    for source in read(ROOT/'config/sources.json')['sources']:
        verify(source,args.input_dir/source['path'])
    videos=[]
    for view in read(ROOT/'config/annotations.json')['views']:
        frames=read(out/'audit'/(view['source']+'_frames.json'))
        assert all(i<len(frames) for i in view['selected_frames'])
        if not view['video']:continue
        path=out/'assets'/(view['id']+'_slow_review.mp4')
        data=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(path)]))
        stream=data['streams'][0]
        expected=view['end_frame']-view['start_frame']+1
        assert int(stream['nb_read_frames'])==expected,(path,stream['nb_read_frames'],expected)
        assert len(data['streams'])==1 and stream['codec_type']=='video'
        videos.append({'file':path.name,'decoded_frames':expected,'duration_seconds':stream['duration'],'muted':True})
    normal=Links();normal.feed((out/'index.html').read_text())
    assert all((out/name).is_file() for name in normal.sources)
    standalone=Links();standalone.feed((out/'Kirk_video_review.html').read_text())
    assert len(standalone.sources)==len(normal.sources)
    assert all(name.startswith('data:') for name in standalone.sources)
    for path in [ROOT/'FINDINGS.md',out/'FINDINGS.md']:
        for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            assert (path.parent/target).is_file(),(path,target)
    manifest=read(out/'audit/output_sha256.json')
    for name,expected in manifest.items():assert sha(out/name)==expected,name
    print(json.dumps({'source_hashes_verified':4,'videos':videos,'html_asset_references_verified':len(normal.sources),
        'standalone_embedded_assets_verified':len(standalone.sources),'markdown_image_links':'passed',
        'output_hashes_verified':len(manifest),'browser_layout_tested':False},indent=2))

if __name__=='__main__':main()
