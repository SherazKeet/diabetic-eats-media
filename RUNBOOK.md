# Diabetic Eats – Daily Reel Runbook

Automated daily Facebook Reel for the **Diabetic Eats** page (Metricool brand/blogId `8110748`, timezone `Asia/Karachi`).

## Audience & strategy
- **International audience (mainly US/UK), not Pakistan.** US spelling, US/UK foods and holidays.
- Post at **6:30 PM Asia/Karachi** (= 8:30 AM New York, 1:30 PM London, 5:30 AM California). Changed from 11 PM on 2026-11-22 at Sheraz's request, based on Metricool's Facebook best-time data.
- Mostly **food** content (the page is "Diabetic Eats"): swaps, myth-busters, plate building, quick recipes, food comparisons, rankings, label reading, eating order, walking after meals. Occasional health topic. Tie into US calendar (holidays, seasons, game days).
- **30–40 seconds, 7–9 scenes** (Sheraz's choice on 2026-11-24, now that reels use cartoon characters and 5 styles; briefly tried 15–20 s). Every scene must earn its place: one idea per scene, and add a mid-reel re-hook around scene 4–5 (e.g. "But here's the surprise…", "Round three is the big one", "And number one might shock you") so people keep watching.
- **Scene 1 is the hook and is fully on screen from the first frame** (the renderer does this automatically for scene 1). The first spoken words must be the hook: a surprising claim, a "stop doing X", a "which wins?", or a quick question. Never a greeting or intro.
- **No ending "comment / follow" scene.** The last scene is the payoff: the strongest takeaway, the winner, or the #1 — so the reel feels complete and loops. Put the question and the share prompt in the caption instead.
- Make it **shareable/saveable**: practical lists, swaps, rankings and "most people don't know" facts.
- Short caption: 1–2 lines of value, then a **share prompt** (e.g. "Send this to someone with diabetes 💚" or "Save this for your next grocery run"), then one easy question, then 4–5 hashtags incl. `#DiabeticEats`. No long source lists.
- First comment: `Educational info only, not medical advice. Talk to your care team about what's right for you. 💚`
- Facts must be accurate and conservative (verify any number with a web search before using it — this includes every number in `fight` bars, `stat` cards and `plate` badges). Never give medication or dosing advice.
- Don't repeat a topic already in `posted.md`.

## Styles — pick ONE per reel based on the topic
Every reel uses one of 5 styles (top-level `"style"` in the script). Each has its own look so the feed stays varied, while the font, captions, `@DiabeticEats` tag and broccoli mascot keep it on-brand. Preview scripts: `scripts/examples/style-*.json`.

| Style | Use it for | Look | Scene recipe (7–9 scenes) |
|---|---|---|---|
| `talk` — **Cartoon Talk** | tips, habits, how-tos, explainers, health news | dark green | 1 `character` hook → 2 `items` → 3 `swap` → 4 `stat` → 5 re-hook `emoji`+faces → 6 `items`/`swap` (how to do it) → 7 `character` payoff |
| `fight` — **Food Fight** | "A vs B", "which is better?", swaps between two foods | red-vs-blue split, VS slam, boxing gloves | 1 `fight` intro (no bars: "A versus B. Which wins?") → 2–5 `fight` + 1 bar each ("Round one…" up to "Round four…"; let the loser win one round to keep it tense) → 6 `fight` with `winner` (crown, confetti, loser turns grey & sad) → 7 `swap` or `character` tip (how to enjoy the winner) |
| `quiz` — **Myth or Fact** | myths, "is X bad?", "does X really…?", surprising facts | game-show blue with spotlight rays | Two rounds: 1 `quiz` → 2 `reveal` → 3 `items`/`stat` (why) → 4 `quiz` ("Round two…", a related claim) → 5 `reveal` → 6 `items`/`swap` (what to do instead) → 7 `character` payoff |
| `kitchen` — **Plate Builder** | quick recipes, meal & snack ideas, breakfast/lunch/dinner plates, "what to eat instead" | warm cream kitchen, gingham tablecloth, chef-hat mascot | 1 `character` hook (food wears a chef hat) → 2 `swap` (the usual meal → the better one) → 3 `plate` (3–4 items drop in + 2 badges) → 4 `steps` (recipe, 3–4 steps) → 5 `stat` (why it works) → 6 `emoji`+faces tip/variation → 7 payoff ("Save this…") |
| `countdown` — **Top Countdown** | rankings, "top 3", best→worst, "3 mistakes", holiday food rankings | orange-to-pink sunset rays | Top 5: 1 intro (`emoji`+faces: "Ranking X from worst to best") → 2–6 `rank` #5 → #1 (`"of": 5`; #1 gets `"talk": true`, crown + confetti) → 7 `character` or `items` takeaway |

**How to pick:**
1. Classify today's topic and use the matching style from the table. If a topic fits another style better with a small reframe, reframe it (e.g. "Is fruit bad?" → `quiz`; "pumpkin vs pecan vs apple pie" → `countdown`; "chips vs popcorn" → `fight`; "breakfast mistakes" → `kitchen` showing the better plate).
2. **Variety:** don't use the same style more than 2 days in a row. When two styles fit, pick the one used least recently (see the Style column in `posted.md`).
3. Say which style you picked and why in the final summary, and log it in `posted.md`.

## Plan
| Date | Topic | Style |
|---|---|---|
| 2026-11-21 | Is honey healthier than sugar? (DONE) | (old) |
| 2026-11-22 | (DONE) 4 Thanksgiving side swaps (cauliflower mash, roasted veg, etc.) — swapped in; original "Thanksgiving plate" overlapped the page's 2026-11-12 Plate Method reel | (old) |
| 2026-11-23 | Eat in this order: veggies & protein first, carbs last (DONE) | (old) |
| 2026-11-24 | Game-day snacks: popcorn vs potato chips — which wins? (DONE) | fight |
| 2026-11-25 | The 10-minute walk after dinner (DONE) | talk |
| 2026-11-26 | Thanksgiving: ranking pumpkin vs pecan vs apple pie (DONE) | countdown |
| 2026-11-27 | "Is fruit bad for diabetes?" — myth or fact (DONE; avoided juice angle — page covered juice vs whole fruit on 2026-11-10) | quiz |
| 2026-11-28 | Breakfast mistakes → build a better breakfast plate (DONE) | kitchen |
| 2026-11-29 | Read a nutrition label in 30 seconds | talk |
| 2026-11-30 | "Sugar-free" doesn't mean carb-free | quiz |
After the plan ends, pick a new topic following the strategy above, choose its style with the rules above, and add both to this table. Keep a healthy mix — roughly 1–2 recipes/plates (`kitchen`) per week.

## Daily steps
0. **Duplicate check (before choosing anything):**
   - Pull the page's reels from the last 60 days with Metricool `getAnalyticsDataByMetrics` (brandId `8110748`, metrics `FBRE02` date, `FBRE05` caption). This includes reels posted by hand or by other tools, not just ones in `posted.md`.
   - Today's topic must not repeat or closely overlap any topic in `posted.md` OR any caption from that list. If it does, swap in a different topic and update the Plan.
   - (Automatic metrics-based changes are paused until December — follow the format rules above, but don't change topics or style on your own based on views/likes yet.)
1. `bash pipeline/setup.sh` (installs Kokoro TTS, downloads the model and builds `kokoro-timed.onnx`, which gives phoneme timings for lip sync).
2. **Pick the style** (see "Styles"), then write `scripts/YYYY-MM-DD.json` — start from `scripts/examples/style-<style>.json`. **7–9 scenes, 30–40 s total.** Keep each `say` to one or two short sentences (about 8–18 words).
   Top level: `"style"`, `"voice": "af_heart"`, `"speed": 1.15`, `"mascot": "🥦"` (always — small talking broccoli in the top-left whenever no other character is talking; wears a chef hat in `kitchen`), `"bg_icons"` (4–6 topic emoji that float in the background).
   Every scene: `say` (narration; numbers as words), `headline` (ALL CAPS, short; letters, numbers and basic punctuation only — symbols like ≠ or arrows get replaced automatically), optional `sub` (no emoji), `accent` hex, optional `mood` (`happy` | `sad` | `fight` | `surprised`), optional `footer` on the last scene (`Educational only. Not medical advice.`).
   Accent colors: `talk` #B6F35C green / #FFC93C yellow / #FF7A59 coral; `fight`, `quiz`, `countdown` #FFD600 (default); `kitchen` (light background) #E07B28 orange / #3E9B4F green / #D64545 red — never pale colors in `kitchen`.
   Each scene uses ONE visual. **At least 2 scenes per reel must show cartoon faces** (`character`, `emoji`+`faces`, `fight`, `rank`, or `plate`/`swap` with `"faces": true`):
   - `character`: one big **talking cartoon food** (googly eyes, blinking, phoneme lip sync, squash & stretch), e.g. `"character": "🥦"`, optional `"with": ["🍿","🥜"]` (1–2 props), optional `"mood"`. Great for hooks and payoffs.
   - `emoji`: 1–4 Noto emoji. Add `"faces": true` to make food emoji into characters (first one talks).
   - `items`: 2–4 rows of [icon, label] (label ≤ 22 chars) revealed as spoken.
   - `steps`: 2–4 numbered recipe steps [emoji, text ≤ 24 chars] revealed as spoken (`kitchen`).
   - `swap`: [[from_emoji, from_label], [to_emoji, to_label]] — "this → that" with ❌/✅ stamps (add `"faces": true` for a sad/happy pair).
   - `stat`: [[label, value], [label, value]] — numbers count up (value like "17g", "37%").
   - `fight`: `{"left": ["🍿","POPCORN"], "right": ["🥔","CHIPS"], "bars": [["FIBER", 3.6, 1.2, "g", "high"]], "winner": "left"}`. Bars: [label, left value, right value, unit, "high" or "low" = which is better]; max 2 bars per scene; compare the SAME serving basis and say it in the narration (e.g. "per snack serving"). Omit `bars` and `winner` for the intro scene.
   - `quiz`: `{"statement": "Sugar-free cookies have no carbs.", "label": "TRUE OR FALSE?", "character": ["🍪","surprised"]}` — statement ≤ 8 words; the 3-2-1 timer runs over the scene.
   - `reveal`: `{"answer": "myth" | "fact", "statement": "short version of the claim"}` — big MYTH/FACT stamp with screen shake.
   - `plate`: `{"items": [["🥚","2 eggs"], ["🥑","½ avocado"], ...], "badges": [["PROTEIN","19g"], ["FIBER","9g"]], "faces": true}` — 2–4 items (labels ≤ 14 chars), up to 3 badges.
   - `rank`: `{"n": 3, "of": 3, "item": "🥧", "mood": "sad"}` — big #n card + ladder; `n: 1` gets a crown + confetti; add `"talk": true` on #1.
   Faces: only on food emoji. Emoji that already have a face (🎃 🦃 animals, smileys) are animated without added eyes — prefer plain food emoji (use 🥧 for any pie). Foods with tuned face positions: 🥦🥕🍿🥑🍎🍅🥔🍋🫐🍞🥚🍓🧁🍩🍪🍊🍌🥜🍯🥗🍇🌽🥒🍗🥧🍠🫑🍐🍑🥛🧃🥤🍫🍰🥯🥐🍚🍝🍕🍔🍟🥥.
3. Render: `python3 pipeline/render.py scripts/YYYY-MM-DD.json out/diabetic-eats-YYYY-MM-DD.mp4` (it warns if lip-sync timings are missing — then re-run setup.sh).
4. Quality check: extract the first frame (`-ss 0`) plus the last frame of each scene and look at them; confirm the hook headline is fully visible at frame 0, nothing overlaps or overflows, faces sit on the food, duration 30–42 s (if outside that, add or cut a scene and re-render), has audio, size < 25 MB.
5. Copy the MP4 to `reels/diabetic-eats-YYYY-MM-DD.mp4`, commit, push to `main`.
6. Confirm `https://raw.githubusercontent.com/SherazKeet/diabetic-eats-media/main/reels/diabetic-eats-YYYY-MM-DD.mp4` returns 200.
7. Metricool `getScheduledPosts` for that date — skip if a reel is already scheduled for that slot (no duplicates).
8. Metricool `createScheduledPost`: blogId `8110748`, `media` = [raw GitHub URL], providers facebook, `facebookData: {"type":"REEL","title":"<title>"}`, `autoPublish: true`, `draft: false`, publicationDate 18:30 Asia/Karachi, caption + firstCommentText.
9. Verify with `getScheduledPosts`: media is on `static.metricool.com`, type REEL, autoPublish true, 18:30 Asia/Karachi, status PENDING.
10. Append a line to `posted.md` (date, topic, **style**, Metricool post id, status) and push.

PENDING = scheduled, not published. Never report success without step 9.
