"""Makes voiceover videos for TikTok / Reels / Shorts.

For each entry in marketing/voiced.json: an AI voice (Kokoro, open source, Apache-2.0) reads the script,
big captions appear line by line, and the game's music plays underneath a gameplay clip.
Output: marketing/voiced/<id>.mp4 and a poster <id>.jpg

Runs on GitHub Actions (see .github/workflows/videos.yml).
Locally without Kokoro:  python3 scripts/voiceover.py --fake-tts   (beeps instead of a voice, to check layout)
"""
import json, os, subprocess, sys, tempfile, textwrap, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, 'marketing', 'voiced.json')
OUT = os.path.join(ROOT, 'marketing', 'voiced')
CLIPS = os.path.join(ROOT, 'marketing', 'clips')
MUSIC = os.path.join(ROOT, 'marketing', 'music', 'loop.m4a')
FONT = os.path.join(ROOT, 'fonts', 'LilitaOne-Regular.ttf')
END_CARD = 2.2          # seconds of end card at the end of every clip
FAKE = '--fake-tts' in sys.argv
ONLY = [a for a in sys.argv[1:] if not a.startswith('--')]


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


_pipe = None
def speak(text, voice, speed, path):
    """Write one line of speech to a WAV file."""
    if FAKE:
        secs = max(0.8, len(text) * 0.055)
        run('ffmpeg', '-y', '-f', 'lavfi', '-i', f'sine=frequency=520:duration={secs}', '-ar', '24000', path)
        return
    global _pipe
    import numpy as np, soundfile as sf
    from kokoro import KPipeline
    if _pipe is None:
        _pipe = KPipeline(lang_code='a')
    parts = []
    for r in _pipe(text, voice=voice, speed=speed):
        a = r.audio if hasattr(r, 'audio') else r[2]
        if hasattr(a, 'cpu'):
            a = a.cpu().numpy()
        parts.append(np.asarray(a, dtype='float32'))
    sf.write(path, np.concatenate(parts), 24000)


def make(video, cfg, tmp):
    clip = os.path.join(CLIPS, video['clip'] + '-clean.mp4')
    total = duration(clip)
    talk_end = total - END_CARD - 0.25          # voice should finish before the end card
    voice, speed = video.get('voice', cfg['voice']), video.get('speed', cfg.get('speed', 1.0))

    # 1) speak each line, lay them out one after another
    t, lines = 0.35, []
    for i, text in enumerate(video['lines']):
        wav = os.path.join(tmp, f"{video['id']}-{i}.wav")
        speak(text, voice, speed, wav)
        d = duration(wav)
        lines.append({'text': text, 'wav': wav, 'start': t, 'dur': d})
        t += d + 0.35
    spoken = t - 0.35
    tempo = 1.0
    if spoken > talk_end:                        # too long: speed the voice up a little (max 18%)
        tempo = min(1.18, spoken / talk_end)
        t = 0.35
        for l in lines:
            l['start'], l['dur'] = t, l['dur'] / tempo
            t += l['dur'] + 0.35 / tempo
        if t > talk_end + 0.6:
            print(f"  warning: script for {video['id']} is too long by {t - talk_end:.1f}s; shorten it")

    # 2) captions: one text file per line, wrapped for a phone screen
    draws = []
    for i, l in enumerate(lines):
        tf = os.path.join(tmp, f"{video['id']}-cap{i}.txt")
        with open(tf, 'w') as f:
            f.write('\n'.join(textwrap.wrap(l['text'], 17)))
        end = l['start'] + l['dur'] + (0.18 if i < len(lines) - 1 else 0.5)
        draws.append(
            f"drawtext=fontfile='{FONT}':textfile='{tf}':text_align=C:fontsize=86:line_spacing=10:"
            f"fontcolor=white:borderw=9:bordercolor=0x2A1B4F:shadowcolor=0x000000@0.35:shadowx=0:shadowy=8:"
            f"x=(w-text_w)/2:y=h*0.42-text_h/2:enable='between(t,{l['start']:.2f},{end:.2f})'")

    # 3) audio: voice lines at their start times + the game's music underneath
    inputs, filters, labels = ['-i', clip, '-stream_loop', '-1', '-i', MUSIC], [], []
    for i, l in enumerate(lines):
        inputs += ['-i', l['wav']]
        at = f"atempo={tempo:.3f}," if tempo != 1.0 else ''
        filters.append(f"[{i + 2}:a]{at}aresample=48000,adelay={int(l['start'] * 1000)}:all=1,volume=1.6[v{i}]")
        labels.append(f"[v{i}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[voice]")
    filters.append(f"[1:a]aresample=48000,volume=0.55,afade=t=out:st={total - 1.2:.2f}:d=1.2[music]")
    filters.append("[voice][music]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    filters.append(f"[0:v]{','.join(draws)}[v]")

    os.makedirs(OUT, exist_ok=True)
    mp4 = os.path.join(OUT, video['id'] + '.mp4')
    run('ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(filters),
        '-map', '[v]', '-map', '[a]', '-t', f'{total:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', mp4)
    poster_t = lines[min(1, len(lines) - 1)]['start'] + 0.3
    run('ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{poster_t:.2f}', '-i', mp4, '-frames:v', '1', '-q:v', '3',
        os.path.join(OUT, video['id'] + '.jpg'))
    print(f"  {video['id']}: {os.path.getsize(mp4) / 1e6:.1f} MB, voice {spoken:.1f}s (tempo {tempo:.2f})")


def main():
    cfg = json.load(open(CFG))
    todo = [v for v in cfg['videos'] if not ONLY or v['id'] in ONLY]
    with tempfile.TemporaryDirectory() as tmp:
        for v in todo:
            make(v, cfg, tmp)
    print(f"made {len(todo)} video(s){' with a stand-in voice' if FAKE else ''}")


if __name__ == '__main__':
    main()
