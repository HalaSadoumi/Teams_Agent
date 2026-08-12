#!/usr/bin/env python3
import json
from pathlib import Path
import re
from collections import Counter

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / 'data' / 'processed' / 'actual'
TRANSCRIPT = WORK / 'transcript' / 'transcript.json'
SCRIPTS_DIR = WORK / 'scripts'
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Parameters
MAX_GAP = 10.0
MIN_SCENE_DURATION = 60.0
MAX_SCENE_DURATION = 300.0
CHAPTER_DURATION = 300.0

# utilities
_word_re = re.compile(r"\w+", re.UNICODE)

FILLER_WORDS = set(["uh","um","eh","euh","bon","alors","genre","vous","savez","en","fait","donc","voila","voilà","d'accord","quoi","hein","c'est","tu","vois","je","veux","dire"]) 

def tokens(text):
    return [w.lower() for w in _word_re.findall(text) if len(w) > 2]

def extract_keywords(text, topn=10):
    toks = tokens(text)
    if not toks:
        return []
    # simple frequency
    freq = Counter(toks)
    # remove short/common tokens
    for w in list(freq):
        if w in FILLER_WORDS:
            del freq[w]
    return [k for k,_ in freq.most_common(topn)]

def topic_similarity(a, b):
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    inter = sa & sb
    uni = sa | sb
    return len(inter) / len(uni) if uni else 0.0

# Clean text similar to script._clean_text
def clean_text(text):
    normalized = re.sub(r"[\r\n]+", " ", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    # remove filler words (naive)
    for fw in sorted(FILLER_WORDS, key=len, reverse=True):
        pattern = r"\b" + re.escape(fw) + r"\b"
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\b(\w+)\s+\1\b", r"\1", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+([?.!,;:])", r"\1", normalized)
    normalized = re.sub(r"^\W+", "", normalized)
    return normalized

# Load transcript segments
if not TRANSCRIPT.exists():
    print('Transcript not found at', TRANSCRIPT)
    raise SystemExit(1)

with open(TRANSCRIPT, 'r', encoding='utf-8') as f:
    data = json.load(f)
segments = data.get('segments', [])
if not segments:
    print('No segments found in transcript')
    raise SystemExit(1)
# Convert to minimal segments list
segs = []
for s in segments:
    segs.append({'start': float(s['start']), 'end': float(s['end']), 'text': s.get('text','')})

# Group segments into buckets by gap
buckets = []
current = [segs[0]]
for seg in segs[1:]:
    if seg['start'] - current[-1]['end'] > MAX_GAP:
        buckets.append(current)
        current = [seg]
    else:
        current.append(seg)
if current:
    buckets.append(current)

# Split buckets by topic into scenes
scenes = []
scene_idx = 1
for bucket in buckets:
    # if small, keep whole
    if len(bucket) < 3:
        parts = [bucket]
    else:
        parts = []
        cur = [bucket[0]]
        cur_kw = extract_keywords(bucket[0]['text'])
        start_time = bucket[0]['start']
        for seg in bucket[1:]:
            seg_kw = extract_keywords(seg['text'])
            sim = topic_similarity(cur_kw, seg_kw)
            elapsed = seg['end'] - start_time
            if elapsed >= MAX_SCENE_DURATION or (elapsed >= MIN_SCENE_DURATION and sim < 0.25):
                parts.append(cur)
                cur = [seg]
                cur_kw = seg_kw
                start_time = seg['start']
            else:
                cur.append(seg)
                if seg_kw:
                    cur_kw = (cur_kw + seg_kw)[:10]
        if cur:
            parts.append(cur)
    for part in parts:
        st = part[0]['start']
        ed = part[-1]['end']
        text = ' '.join(p['text'] for p in part).strip()
        scenes.append({'id': f"scene_{scene_idx:03d}", 'start': st, 'end': ed, 'transcript': text})
        scene_idx += 1

# Build chapters semantically
chapters = []
if scenes:
    cur_scenes = [scenes[0]]
    cur_kw = extract_keywords(scenes[0]['transcript'])
    cur_start = scenes[0]['start']
    ch_idx = 1
    for sc in scenes[1:]:
        sc_kw = extract_keywords(sc['transcript'])
        sim = topic_similarity(cur_kw, sc_kw)
        elapsed = sc['end'] - cur_start
        if (elapsed >= CHAPTER_DURATION and sim < 0.25) or elapsed >= CHAPTER_DURATION * 1.5:
            # make chapter
            title_kw = extract_keywords(cur_scenes[0]['transcript'], topn=3)
            title = ' · '.join(w.capitalize() for w in title_kw) if title_kw else f'Chapter {ch_idx:02d}'
            chapters.append({'id': f'chapter_{ch_idx:02d}', 'title': title, 'start': cur_start, 'end': cur_scenes[-1]['end'], 'scenes':[s['id'] for s in cur_scenes]})
            ch_idx += 1
            cur_scenes = [sc]
            cur_kw = sc_kw
            cur_start = sc['start']
        else:
            cur_scenes.append(sc)
            if sc_kw:
                cur_kw = (cur_kw + sc_kw)[:10]
    if cur_scenes:
        title_kw = extract_keywords(cur_scenes[0]['transcript'], topn=3)
        title = ' · '.join(w.capitalize() for w in title_kw) if title_kw else f'Chapter {ch_idx:02d}'
        chapters.append({'id': f'chapter_{ch_idx:02d}', 'title': title, 'start': cur_start, 'end': cur_scenes[-1]['end'], 'scenes':[s['id'] for s in cur_scenes]})

# Rewrite scenes using clean_text
rewritten_scenes = []
for sc in scenes:
    cleaned = clean_text(sc['transcript'])
    rewritten_scenes.append({'id': sc['id'], 'start': sc['start'], 'end': sc['end'], 'transcript': cleaned})

# For each chapter, create a narration file combining scenes
output_storyboard = []
for ch in chapters:
    ch_scenes = [s for s in rewritten_scenes if s['id'] in ch['scenes']]
    narration = '\n\n'.join(s['transcript'] for s in ch_scenes)
    fname = SCRIPTS_DIR / f"{ch['id']}_narration.txt"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(f"{ch['title']}\n\n")
        f.write(narration)
    output_storyboard.append({'chapter_id': ch['id'], 'title': ch['title'], 'narration_file': str(fname.relative_to(REPO))})

# Save outputs
with open(WORK / 'storyboard_rewritten_all.json', 'w', encoding='utf-8') as f:
    json.dump(output_storyboard, f, ensure_ascii=False, indent=2)
with open(WORK / 'chapters_rewritten.json', 'w', encoding='utf-8') as f:
    json.dump(chapters, f, ensure_ascii=False, indent=2)
with open(WORK / 'scenes_rewritten.json', 'w', encoding='utf-8') as f:
    json.dump(rewritten_scenes, f, ensure_ascii=False, indent=2)

print('Chapters:', len(chapters))
print('Scenes:', len(scenes))
print('Narration files written to', SCRIPTS_DIR)
