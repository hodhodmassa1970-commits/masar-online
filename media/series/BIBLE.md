# هيا — سلسلة «من حياتها» (Series bible)

كل حلقة تُبنى بنفس المحرّك، بنفس الصوت، وبنفس خيط الهوية البصري. الهدف:
**ممكن إنتاج حلقة جديدة كاملة (30–60 ثانية، 9:16، صوت + ترجمة + موسيقى) بأمر واحد.**

## 1) ثوابت الهوية (لا تتغيّر في أي حلقة)
| العنصر | القاعدة |
|---|---|
| الوجه | مرجع واحد: `media/reference.jpg` — يُمرَّر دائماً كصورة الإدخال لكل توليد صورة، حتى الطفولة والمراهقة (نفس ملامح العينين والابتسامة، مع تغيير العمر فقط) |
| صوت هيا | `voice-03` · لهجة شامية ناعمة · المرجع الإلقائي: `media/audio/a2.mp3` — لا يُبدَّل الصوت (انظر `haya_voice.json`) |
| القلادة | فضية رقيقة بحجر أزرق صغير = **خيط بصري عبر كل العُمر** (تظهر في كل حقبة: الطفولة، الجامعة، الرفض، البناء، المسرح، العودة) |
| اللوحة اللونية | كريمي/أبيض في الملابس · تدرّج Teal & Gold · حبيبات فيلمية · `vignette PI/4.2` |
| الإطار | 9:16 ‏(1080×1920) · 30fps · ترجمة بـ Noto Kufi + العناوين الذهبية بـ Amiri |
| البنية | لقطة/مقطع صوتي واحد لكل مشهد · `LEAD=0.9s` صمت قبل الكلام · تلاشي 0.85s بين المشاهد الحسّاسة، قطع سريع (0.041s) للطاقات العالية |

## 2) الخُطّة (6 حلقات)
| # | العنوان | الحقبة | اللقطات (ملفات `media/frames/`) | الحالة |
|---|---|---|---|---|
| — | **الانطلاقة** (الفيلم الحالي) | المسرح | `s1_run … s7_finale.png` | ✅ `media/haya_shami_vertical.mp4` |
| E1 | **الدفتر الأول** | الطفولة/المدرسة | `e1_terrace`, `e1_kitchen`, `e1_classroom` | 🔨 جاهز للتوليد |
| E2 | **السنة الصعبة** | 22 سنة — الرفض | `e2_night` | ✅ صورة مفتاحية |
| E3 | **البناء** | 27 سنة — الاستوديو الصغير | `e3_studio` | ✅ صورة مفتاحية |
| E4 | **اثنا عشر شخصاً** | 29 سنة — أول لقاء | `e4_hall` | ⏳ بانتظار توليد (حصة الصور) |
| E5 | **بعد أن خرج الضوء** | ليلة الانطلاقة، القاعة الفارغة | `e5_after` | ⏳ بانتظار توليد |
| E6 | **العودة** | بلدتها — ساحة المدرسة | `e6_school` | ⏳ بانتظار توليد |

## 3) إنتاج حلقة
1. **صور**: `generate_image` مع `images:[media/reference.jpg]` ووصف يحمل: العمر الجديد + القلادة + كريمي + Teal & Gold، وتُحفظ في `media/frames/eN_*.png`.
2. **صوت**: 2–4 مقاطع `generate_speech` بـ `voice-03` إلى `media/series/eN/a1.mp3 …`.
3. **إعداد**: `media/series/eN/eN.json` (الحلقة الأولى مثال كامل جاهز) — `seg` للمقاطع و`shots` للمشاهد والنصوص والـ overlays.
4. **تشغيل**:
   ```
   /home/user/.venv/bin/python /home/user/masar-online/media/episode.py \
       /home/user/masar-online/media/series/e1/e1.json
   ```
   الناتج في `media/series/e1/out/`: نسخة HD · نسخة ويب خفيفة · `*_keyart.png` · `*_teaser.gif`.

## 4) قواعد جودة مُثبَّتة في المحرّك (لا تُكسر)
- طبقات الرسوم تُحفظ **RGBA شفافة**، وإلا يختفي المزج.
- كل لقطة تُرمَّز بهامش **+3 إطارات** لأن `xfade` عند `offset+duration == نهاية اللقطة الأولى` يقصّ الفيلم.
- `colorbalance` في النسخة المضمّنة من ffmpeg لا تعرف `ms/hs` — نستخدم `rm/gm/bm/rh/gh/bh/rs/gs/bs` فقط.
- مستوى الصوت: كسب تلقائي يرفع الكلام إلى ذروة 0.88 والموسيقى 0.30 مع ducking ‏0.4–0.52 · ثم `alimiter 0.97`.
- الترميز النهائي 1-pass ‏crf 24 للـ 1080×1920 (الحبيبات ترفع الـ bitrate بلا فايدة) + نسخة 540×960 crf 30 للويب.

## 5) ملاحظات
- كل الوسائط **داخل المستودع** ومدفوعة على الفرع، لأن مساحة العمل تُصفَّر بين الجولات وكل ما خارج المستودع يضيع.
- `media/work_e*/` مستثنى عبر `.gitignore` (وسائط وسيطة كبيرة).

## Overlay schema (exact keys — verified against build_reel.tiles())
- `kicker`: `{ "t": "<text>", "a": <start s>, "b": <hold s> }`  (small kufi line, bottom, y=.935)
- `title`:  `{ "t": "<text>", "line": <int, index into that shot's "lines">, "a": <s before that line>, "hold": <s after> }` (gold Amiri 52, y=.125)
- `motto`:  `{ "t": "<text>", "a": <start s> }` (Amiri 22, top, y=.095)
- `endcard`:{ "main": "<text>", "sub": "<text>" }` on the LAST shot only (Amiri 62 y=.36 + kufi 17)
- `lines`: list of subtitle strings; `|` forces a line break; timing is proportional to
  a per-line weight `max(6, len + 4*'.' + 7*'!' + 6*'…')` spread over the segment's speech duration.

## Units (do not mix up)
- `rays` = strength fraction 0.0–1.0 · `conf` = particle COUNT 60–300 · `cx` = crop-band fraction 0–1
- `z` = [zoom0, zoom1] around 1.00–1.10 · `p` = [px0,py0,px1,py1] pan focal fractions 0–1
- `tin` = incoming transition overlap: 0.0 first shot, 0.85 dissolve, 0.04 hard cut
- `seg[]`: `tail` = breathing room after the line, `minimum` = force shot length (only the last shot of a segment)

## Engine bugs fixed (2026-10-25) — already in build_reel.py, do not re-introduce
- `score()` cue vars renamed `q1/q2/q3` (they shadowed the shaker loop's local `t2` ndarray → "truth value of an array").
- `final()` audio input indices are now `len(SHOTS)` / `len(SHOTS)+1` (were hardcoded 7/8 → "Invalid file index 7" on a 3-shot episode).
- poster/teaser seeks clamp to the number of segments; `episode.py` accepts a stage list and auto-prepends `timeline` (so `timeline score final` resumes a render without re-tiling).

## Status (render = full film: hd/web mp4 + poster.jpg + teaser.gif + keyart.png in media/series/eN/out/)
- pilot `media/haya_shami_vertical.mp4` — DONE, committed.
- E1 الدفتر الأول — **rendered 37.02 s** (3 shots on `e1_kitchen.png`; terrace + classroom art still missing).
- E2 السنة الصعبة — **rendered 35.56 s** (3 shots, one plate `e2_night.png`).
- E3 البناء — **rendered 31.74 s** (`e3_studio.png` ×2 + pilot `s4_heart.png` for the launch night).
- E4 اثنا عشر شخصاً / E5 بعد أن خرج الضوء / E6 العودة — storyboard in this file, VO + frames NOT yet generated.
- `generate_image` cap: 10 calls per turn, AND upstream 429s count toward it. Batch 3–4 per turn.
- TODO: child frames read lighter-haired than Haya — regenerate `e1_kitchen/e1_terrace/e1_classroom`
  with "same facial identity as the reference, dark brown hair, olive skin" and re-render E1.

## IDENTITY LOCK (2026-10-25, from the user's own portrait)
- Canonical face/outfit reference is now **`media/haya_portrait.png`** (the user's image): long wavy
  **blonde** hair, blue-green eyes, fair glowing skin, cute bright smile. (Earlier note about "dark hair"
  was WRONG — the pilot frames already match; do not "correct" it again.)
- Every `generate_image` call passes `images=["media/haya_portrait.png"]`.
- **Outfit rule (user asked explicitly):** the look must be *coordinated and cute* — cream/white tailored
  blazer + matching trousers, **pointed white kitten heels with gold buckle**, **tan-beige structured
  leather handbag** (silk scarf tied to the handle), gold hoops, slim gold watch, gold pendant, ring.
  Shoes/bag/accessories always read as one set, never random.
- **Energy rule:** she is *social and kinetic* — walking, turning, a twirl, phone out filming a selfie vlog,
  greeting her audience. Prefer hard cuts (`tin: 0.04`) and wider zoom (`z` up to 1.13) over long dissolves.
- She is a **social-media influencer who works in advertising** with a real audience ("أميرة الجماهير").
- Plates are now generated **native 9:16** → prep's crop band has ~90 px slack, so use `cx: 0.50`
  (0.62 only to push a composition past a mirror/reflection). The old 16:9 cx-band trick no longer applies.

## g1 · "مسا الخير حبايبي" — RENDERED (19.42 s), pushed a550153
Lines spoken verbatim in `voice-03` (never re-audition her): "مسا الخير حبايبي!" / "ما في أحلى من السهر
بالبيت اللي بيشعرك بالراحة، وبرا البيت اللي بيشعرك بالسعادة." / "أنا هيا… أميرة الجماهير. بحييكن!"
Shots: hg_mirror → hg_door → hg_walk (selfie vlog) → hg_spin (confetti). Files: `media/series/g1/out/`
(hd 9.3 MB, web 1.7 MB, preview gif 1.9 MB = the one that plays in the Arena viewer).

## e0 · «الحلقة الأولى · البداية» — RENDERED (36.85 s), pushed 2aade35
Her world as an advertising influencer: `h0_studio` (ring-light, phone on tripod, REC on screen) →
`h0_set` (billboard of her own campaign behind her) → `h0_phone` (night, reading comments; gold motto
«إحنا سوا») → `h0_meet` (first café meetup, followers filming her, one hands her a letter).
Lines in `voice-03`: «هلا فيكن! أنا هيا…» / «شغلي بالإعلانات: بكتب الفكرة، وبصوّر بإيدي، وبختار الضوّة.» /
«وبالليل بقرا التعليقات، واحد واحد. في تعليق وحدا… يغيّرلك كل شي.» / «ولما التقينا بأول قهوة، صار عندي
الجواب: الجمهور مش أرقام. الجمهور ناس.»
Note: `cx` must aim at her face — 16:9 plates (studio 0.28, phone 0.64), native-9:16 plates 0.50.

## SERIES COMPLETE — batch of 2026-10-25 (12:01 → 12:41, `media/series/batch.sh`)
All eight films rendered, 9:16 1080x1920 30fps, `voice-03`, burned Arabic subtitles, gold Amiri titles.
Order of life: **e1** الدفتر الأول 37.0 ث · **e2** السنة الصعبة 35.6 · **e3** البناء 31.7 ·
**e4** اثنا عشر شخصاً 37.6 · **e5** بعد أن خرج الضوء 33.1 · **e6** العودة 33.6 · then the present-day pair
**e0** البداية (الإعلانات) 36.9 · **g1** مسا الخير حبايبي 19.4. Total ≈ 4 min of film.
- `e1` re-rendered: shot1+shot2 now use `e1_classroom.png` (her first audience) instead of the kitchen plate.
- `e6` deliberately cuts to `e1_classroom.png` for its middle shot (memory echo of the same classroom).
- `e5` last shot reuses pilot `s6_kneel.png` (crowd, arms open) for «نحنا اللي عملناه».
- New frames this batch: `e1_classroom`, `e4_hall`, `e5_after`, `e6_school` (all native 9:16 → `cx: 0.50`).
- `e1_terrace.png` **could not be generated** (model returned no image twice — retry with a softer prompt,
  e.g. avoid "eight-year-old" + face reference together, or generate the child without the identity ref).
- `media/recap.py` → `media/series/poster_wall.png` + `haya_series_recap.gif` (1.05 MB, plays in the viewer).
- Per-episode viewer-friendly file is `haya_eN_preview.gif` (≤2 MB); `haya_eN_hd.mp4` must be downloaded
  (raw.githubusercontent URL) — MP4 never plays inline here.
- Known cosmetic debt: `e4_hall` banner has garbled English and ~25 people instead of 12;
  `e6_school` banner is English too. Fix = regenerate those two plates with "exactly twelve people" /
  Arabic lettering, then re-render e4 and e6 only.

## 16:9 (landscape / YouTube) mode — added 2026-10-25
`AR=16:9 python media/episode.py media/series/<e>/<e>.json` → W,H = 1920x1080, tiles 960x540,
type sizes x0.72 (`ts()`), web copy at W//2, badge says "16:9 · 1080", teaser gif 430 px wide.
Outputs are written next to the vertical ones with a `_land` suffix (`haya_g1_land_hd.mp4` …) and the
vertical files are never touched (`episode.py` only clears files starting with `slug+suffix`).
Framing of a tall plate in a wide frame (v2, `media/build_reel.py::prep`):
  • default `panel` — the plate scaled to 1.18x frame height, positioned by `cx` (0=left,1=right) and
    `cy` (which slice survives the 18% crop; .30 keeps faces high), composited over a blurred,
    darkened cover of itself through a Gaussian-blurred mask → feathered edges, no pasted-box look.
  • `"fill": "bleed"` — full-frame 16:9 crop of the tall plate at `cy` (no bars). Used for the crowd /
    venue beats (`s5_crowd`, `s6_kneel`, `s7_finale`) where losing the vertical is fine.
  • a plate already wider than 1.7 is used at full width (cx slides the window).
Landscape cuts delivered: **g1** (19.5 ث), **e0** (37.0 ث), **pilot** (50.2 ث) — `_land_web.mp4` ≈ 1.6-5.5 MB.
`media/series/pilot/pilot.json` now carries the launch reel as data (7 shots / 4 segs, audio copied into
that folder), so the pilot renders in either format too.
Fast re-cut trick: when only framing changed, run `… <e>.json timeline prep clips speech score final`
— the 960x540 tiles are still valid, which cuts ~40% of the render time.
`media/recap.py` accepts `RECAP_LAND=1 RECAP_EPS=g1,e0,pilot RECAP_SFX=_land RECAP_OUT=… RECAP_WALL=…`.

## Ops notes (hard-won, 2026-10-25/26)
- The sandbox is wiped roughly every 1-2 h (`/home/user/.venv` and every untracked file die with it).
  Long render batches MUST `git add && commit && push` after **each** episode — that is why
  `batch_land3.sh` commits per-episode; after a wipe, `git fetch && git reset --hard FETCH_HEAD`
  plus a venv rebuild brings everything back in ~40 s.
- After a wipe, resume a landscape batch with the episode list, e.g.
  `EPS="e3 e4 e5 e6" bash media/series/batch_land3.sh`.
- 2 cores only: a 3-shot 16:9 episode ≈ 9 min (tiles 5, clips 3, final 1.5). Do not run two lanes.
- `media/recap_frame.py` now derives `haya_<ep>` from the folder name, so it works for every episode
  (it used to hold a 3-item dict and crashed with KeyError on e1).
- Landscape wall/strip: `RECAP_LAND=1 RECAP_EPS=<list> RECAP_SFX=_land RECAP_OUT=haya_land_recap.gif
  RECAP_WALL=land_wall python media/recap.py` — re-run it as episodes land; it skips missing ones.

## Brand opener — `media/brand/` (4.2 s, both formats)
`opener.py` draws the sting with the film engine itself: darkened `frames/s4_heart.png` plate (brightness
.47) + `rays()` sweep + `confetti()/bokeh()` + gold Amiri logotype **أميرة الجماهير** over an expanding
gold rule, kicker «مسلسل هيا» first, sub-line «ثماني حلقات من حكايتها» last; then the same grade chain
as `clips()` (eq → colorbalance → vignette PI/4.2 → noise → unsharp) so it never looks pasted on.
Cue (`cue()`) is synthesized at 122 BPM: sub pad 55/110/164.8 Hz, noise riser to t=.78, soft 96 Hz
impact exactly when the logotype lands, bell arpeggio on the 8ths, and a −0.28 s fade so the film's own
music starts clean.  Timeline (s): .30 kicker · .62 logo (zoom 1.07→1.00) · .95 rule · 1.35 sub · 3.72 fade-out.
Run `python media/brand/opener.py` (writes `opener_vert.mp4`) and `AR=16:9 …` (writes `opener_land.mp4`).

`attach.py <film.mp4>…` (or `--all`) prepends the opener, probing each target's own size/fps and
matching the opener to it → `<name>_op.mp4` next to the source (nothing overwritten).
Opened cuts exist for all 9 films in both formats: `haya_<ep>_web_op.mp4`, `haya_<ep>_land_web_op.mp4`.
HD opened versions are not committed (gitignored) — regenerate with the same script pointed at the HD file.

Repo housekeeping: `media/brand/work/` (the 126 PNG frames) is scratch and gitignored — delete after runs;
the pack is ~400 MiB, so if it ever needs trimming, the first candidates are the un-opened `_web.mp4`
duplicates or the per-episode `*_keyart.png` (superseded by `media/series/land_wall.jpg` + `keyart.jpg`).
