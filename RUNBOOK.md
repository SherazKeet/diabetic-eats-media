# Diabetic Eats – Daily Reel Runbook

Automated daily Facebook Reel for the **Diabetic Eats** page (Metricool brand/blogId `8110748`, timezone `Asia/Karachi`).

## Audience & strategy
- **International audience (mainly US/UK), not Pakistan.** US spelling, US/UK foods and holidays.
- Post at **11:00 PM Asia/Karachi** (= 1 PM New York, 6 PM London, 10 AM California).
- Mostly **food** content (the page is "Diabetic Eats"): swaps, myth-busters, plate building, food comparisons, label reading, eating order, walking after meals. Occasional health topic. Tie into US calendar (holidays, seasons).
- 30–40 sec. **Hook in the first 2 seconds** (surprising claim or question, never a greeting). One idea per scene. End with an easy comment question + "follow for more".
- Short caption: 2–3 lines, one question, 4–5 hashtags incl. `#DiabeticEats`. No long source lists.
- First comment: `Educational info only, not medical advice. Talk to your care team about what's right for you. 💚`
- Facts must be accurate and conservative (verify any number with a web search before using it). Never give medication or dosing advice.
- Don't repeat a topic already in `posted.md`.

## Plan
| Date | Topic |
|---|---|
| 2026-11-21 | Is honey healthier than sugar? (DONE) |
| 2026-11-22 | Build a diabetes-friendly Thanksgiving plate |
| 2026-11-23 | Eat in this order: veggies & protein first, carbs last |
| 2026-11-24 | 4 holiday side swaps (cauliflower mash, roasted veg, etc.) |
| 2026-11-25 | The 10-minute walk after dinner |
| 2026-11-26 | Thanksgiving: pumpkin vs pecan vs apple pie — the smarter slice |
| 2026-11-27 | "Is fruit bad for diabetes?" — berries, whole fruit, pair with protein |
| 2026-11-28 | 3 breakfast mistakes + what to eat instead |
| 2026-11-29 | Read a nutrition label in 30 seconds |
| 2026-11-30 | "Sugar-free" doesn't mean carb-free |
After the plan ends, pick a new topic following the strategy above and add it to this table.

## Daily steps
1. `bash pipeline/setup.sh` (installs Kokoro TTS + model into `/home/claude/tts`).
2. Write `scripts/YYYY-MM-DD.json` (see `scripts/2026-11-21.json` for the format). 7–8 scenes; scene fields: `say` (narration), `headline` (ALL CAPS, short), optional `sub` (no emoji), `emoji` (1–4 Noto emoji) **or** `stat` ([[label, value], [label, value]]), `accent` hex, optional `footer` on the last scene (`Educational only. Not medical advice.`). Voice `af_heart`, speed `1.1`. Write numbers as words in `say`.
3. Render: `python3 pipeline/render.py scripts/YYYY-MM-DD.json out/diabetic-eats-YYYY-MM-DD.mp4`
4. Quality check: extract 3 frames (`ffmpeg -ss <t> -i ... -frames:v 1 f.jpg`) and look at them; confirm duration 25–45 s, has audio, size < 25 MB. Fix and re-render if text overflows or looks wrong.
5. Copy the MP4 to `reels/diabetic-eats-YYYY-MM-DD.mp4`, commit, push to `main`.
6. Confirm `https://raw.githubusercontent.com/SherazKeet/diabetic-eats-media/main/reels/diabetic-eats-YYYY-MM-DD.mp4` returns 200.
7. Metricool `getScheduledPosts` for that date — skip if a reel is already scheduled for that slot (no duplicates).
8. Metricool `createScheduledPost`: blogId `8110748`, `media` = [raw GitHub URL], providers facebook, `facebookData: {"type":"REEL","title":"<title>"}`, `autoPublish: true`, `draft: false`, publicationDate 23:00 Asia/Karachi, caption + firstCommentText.
9. Verify with `getScheduledPosts`: media is on `static.metricool.com`, type REEL, autoPublish true, 23:00 Asia/Karachi, status PENDING.
10. Append a line to `posted.md` (date, topic, Metricool post id, status) and push.

PENDING = scheduled, not published. Never report success without step 9.
