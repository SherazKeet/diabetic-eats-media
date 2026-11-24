# Diabetic Eats – Daily Reel Runbook

Automated daily Facebook Reel for the **Diabetic Eats** page (Metricool brand/blogId `8110748`, timezone `Asia/Karachi`).

## Audience & strategy
- **International audience (mainly US/UK), not Pakistan.** US spelling, US/UK foods and holidays.
- Post at **6:30 PM Asia/Karachi** (= 8:30 AM New York, 1:30 PM London, 5:30 AM California). Changed from 11 PM on 2026-11-22 at Sheraz's request, based on Metricool's Facebook best-time data.
- Mostly **food** content (the page is "Diabetic Eats"): swaps, myth-busters, plate building, food comparisons, label reading, eating order, walking after meals. Occasional health topic. Tie into US calendar (holidays, seasons).
- **15–20 seconds, 4–5 scenes** (changed 2026-11-24: viewers were only watching 4–5 s of 35–40 s reels, which capped reach at ~200–300 views). Cut anything that isn't essential.
- **Scene 1 is the hook and is fully on screen from the first frame** (the renderer does this automatically for scene 1). The first spoken words must be the hook: a surprising claim, a "stop doing X", or a quick question. Never a greeting or intro.
- **No ending "comment / follow" scene.** The last scene is the payoff: the strongest takeaway or surprising fact, so the reel feels complete and loops. Put the question and the share prompt in the caption instead.
- Make it **shareable/saveable**: practical lists, swaps and "most people don't know" facts.
- Short caption: 1–2 lines of value, then a **share prompt** (e.g. "Send this to someone with diabetes 💚" or "Save this for your next grocery run"), then one easy question, then 4–5 hashtags incl. `#DiabeticEats`. No long source lists.
- First comment: `Educational info only, not medical advice. Talk to your care team about what's right for you. 💚`
- Facts must be accurate and conservative (verify any number with a web search before using it). Never give medication or dosing advice.
- Don't repeat a topic already in `posted.md`.

## Plan
| Date | Topic |
|---|---|
| 2026-11-21 | Is honey healthier than sugar? (DONE) |
| 2026-11-22 | (DONE) 4 Thanksgiving side swaps (cauliflower mash, roasted veg, etc.) — swapped in; original "Thanksgiving plate" overlapped the page's 2026-11-12 Plate Method reel |
| 2026-11-23 | Eat in this order: veggies & protein first, carbs last (DONE) |
| 2026-11-24 | Game-day snacks: popcorn vs chips vs nuts — the smarter bowl |
| 2026-11-25 | The 10-minute walk after dinner |
| 2026-11-26 | Thanksgiving: pumpkin vs pecan vs apple pie — the smarter slice |
| 2026-11-27 | "Is fruit bad for diabetes?" — berries, whole fruit, pair with protein |
| 2026-11-28 | 3 breakfast mistakes + what to eat instead |
| 2026-11-29 | Read a nutrition label in 30 seconds |
| 2026-11-30 | "Sugar-free" doesn't mean carb-free |
After the plan ends, pick a new topic following the strategy above and add it to this table.

## Daily steps
0. **Duplicate check (before choosing anything):**
   - Pull the page's reels from the last 60 days with Metricool `getAnalyticsDataByMetrics` (brandId `8110748`, metrics `FBRE02` date, `FBRE05` caption). This includes reels posted by hand or by other tools, not just ones in `posted.md`.
   - Today's topic must not repeat or closely overlap any topic in `posted.md` OR any caption from that list. If it does, swap in a different topic and update the Plan.
   - (Automatic metrics-based changes are paused until December — follow the format rules above, but don't change topics or style on your own based on views/likes yet.)
1. `bash pipeline/setup.sh` (installs Kokoro TTS + model into `/home/claude/tts`).
2. Write `scripts/YYYY-MM-DD.json` (examples: `scripts/2026-11-21.json`, `scripts/example-v2.json`). **4–5 scenes, 15–20 s total.** Keep each `say` to one short sentence (about 6–14 words). Top level: `voice` `af_heart`, `speed` `1.15`, `bg_icons` (4–6 topic emoji that float in the background, e.g. ["🦃","🥧","🥦"]).
   Every scene: `say` (narration; numbers as words), `headline` (ALL CAPS, short — max 2 lines on `items` scenes), optional `sub` (no emoji), `accent` hex (#FFC93C yellow, #FF7A59 coral for warnings, #B6F35C green for good choices), optional `footer` on the last scene (`Educational only. Not medical advice.`).
   Each scene uses ONE visual — **mix them, use at least 3 different types per reel** (scene 1 should be `emoji`, `stat` or `swap` with a big, bold headline):
   - `emoji`: 1–4 Noto emoji (bouncing, glowing) — good for hooks.
   - `items`: 2–4 rows of [icon, label] (✅/❌/food emoji, label ≤ 22 chars) revealed as they're spoken — good for lists/tips.
   - `swap`: [[from_emoji, from_label], [to_emoji, to_label]] — animated "this → that" with ❌/✅ stamps.
   - `stat`: [[label, value], [label, value]] — numbers count up (value like "17g").
3. Render: `python3 pipeline/render.py scripts/YYYY-MM-DD.json out/diabetic-eats-YYYY-MM-DD.mp4`
4. Quality check: extract 3 frames (`ffmpeg -ss <t> -i ... -frames:v 1 f.jpg`) and look at them; confirm duration 15–22 s (if longer, cut words or a scene and re-render); also check the very first frame (`-ss 0`) shows the full hook headline, has audio, size < 25 MB. Fix and re-render if text overflows or looks wrong.
5. Copy the MP4 to `reels/diabetic-eats-YYYY-MM-DD.mp4`, commit, push to `main`.
6. Confirm `https://raw.githubusercontent.com/SherazKeet/diabetic-eats-media/main/reels/diabetic-eats-YYYY-MM-DD.mp4` returns 200.
7. Metricool `getScheduledPosts` for that date — skip if a reel is already scheduled for that slot (no duplicates).
8. Metricool `createScheduledPost`: blogId `8110748`, `media` = [raw GitHub URL], providers facebook, `facebookData: {"type":"REEL","title":"<title>"}`, `autoPublish: true`, `draft: false`, publicationDate 18:30 Asia/Karachi, caption + firstCommentText.
9. Verify with `getScheduledPosts`: media is on `static.metricool.com`, type REEL, autoPublish true, 18:30 Asia/Karachi, status PENDING.
10. Append a line to `posted.md` (date, topic, Metricool post id, status) and push.

PENDING = scheduled, not published. Never report success without step 9.
