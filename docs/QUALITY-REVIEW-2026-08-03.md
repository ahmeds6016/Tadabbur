# Tadabbur Phase 2 product-quality review — 2026-08-03

**Status:** Analysis only; no finding was implemented.

**Production reviewed:** `tafsir-backend-00260-m9l` and `tafsir-frontend-00302-8ls`; live probes performed 2026-08-13.

**North star:** Make it easier for a person to learn the meaning of the Qur'an and practice tadabbur.

## Executive view

The product already has a valuable core: a guest can choose any verse, see clear Arabic and translation, receive layered explanation, follow related verses, and get a verse-specific reflection question. The strongest live answers did ground the verse in context before moving to application. However, the review found one immediate P0 trust defect: a live Ayat al-Kursi response attributed a composite report to Sahih Muslim even though the cited Muslim report omits the added clause. Because cached answers have no TTL, citation validation must come before further prompt polish.

The best low-effort product wins are to show the existing reflection question to guests, count cached studies toward progress, expose real timing/cache instrumentation, and label source coverage instead of silently removing unavailable sources. The next larger investment should make the first screen useful immediately: show the already-available verse and translation while commentary is being prepared, then reveal the answer progressively. Persona work should follow a defined learning contract rather than relying mainly on tone and vocabulary instructions.

Rank below is by expected impact per effort, with scripture/scholarship correctness taking precedence over implementation size.

| Rank | Finding | Severity | Effort | Expected user impact |
|---:|---|---|:---:|---|
| 1 | Hadith attribution can be composite or wrong | **P0** | M | Critical trust and correctness |
| 2 | Guests do not see the generated reflection question | P1 | S | Very high; restores the core tadabbur action |
| 3 | Cached studies do not count as explored verses | P1 | S | High; fixes progress for the most-read verses |
| 4 | Shared pages accept unverified tafsir content | P1 trust | M | High; prevents branded misinformation |
| 5 | Source coverage silently degrades and plan metadata is stale | P1 | M | High; makes evidence and limitations legible |
| 6 | “What should I read next?” is generated but not delivered | P1 | M | High; creates a learning path beyond one answer |
| 7 | Timing metrics are computed but never returned | P1 enabler | S | Medium-high; enables evidence-led latency work |
| 8 | A user waits 17–28 seconds before seeing any insight | P1 | M | High; makes cold responses useful immediately |
| 9 | Persona adaptation is narrower than the product promise | P1 quality | M | High; improves comprehension at each level |
| 10 | Topic-first learners have no direct path | P2 | L | High, but a larger retrieval/product change |
| 11 | Core verse controls and live states need accessibility names | P2 | S | Medium-high; removes avoidable access barriers |
| 12 | Streaks reward successful searches more than reflection | P2 | M | Medium; aligns motivation with learning |
| 13 | Output/cache tuning is unmeasured | P2 | S | Medium; lowers tail latency and spend safely |
| 14 | Reliability debt still interrupts first-run and admin paths | P2 | M | Medium; prevents avoidable breakage and abuse |

## Method, constraints, and corrections to the kickoff assumptions

- Reviewed the complete `/tafsir` path, `build_enhanced_prompt`, personas, source routing, precomputed plans, results UI, guest/auth flow, reflection/progress/badge logic, recommendations, sharing, Arabic styles, and the relevant debt in `docs/AUDIT-2026-08-01.md`.
- Probed the live API directly. Four calls took long enough to be conservatively counted as potentially uncached generations, below the budget of eight. Three warm repeats/persona-body probes and one pre-generation clarification response were also observed. No Firestore, gcloud, deployment, billing, or secrets access was attempted.
- A browser was unavailable in this environment. UI evidence below is code-trace evidence rather than a screenshot or visual-device audit; color contrast and real screen-reader behavior still need a browser/device pass.
- The kickoff says `perf_metrics` is in the response. In the deployed revision it is not. The handler initializes it at `backend/app.py:6749-6759` and records early stages, but none of the cache or generation returns attach it (`backend/app.py:6904-6935`, `7227-7228`). Every live response omitted it.
- The plan metadata says 6,229 total verses, 3,829 successful plans, four deterministic-only plans, and four failures. Enumerating the current JSON instead finds all 6,236 verse keys: 6,170 contain at least one `gemini`/`both` origin and 66 are entirely deterministic. Therefore there is no current verse key with no plan object. Verse 6:57 was used as the honest degraded test because its stored base plan is deterministic-only.

### Live observations

Times are client-observed end-to-end latency, not backend stage timings. A long time does not prove a cache miss because the response exposes neither cache status nor timing stages.

| Query | Request variation | Observed time | Relevant result |
|---|---|---:|---|
| 2:255 | guest default | 16.475s, then 0.491s | Structured answer; first hadith exposed the P0 attribution defect |
| 1:5 | `new_revert`, `curious_explorer`, `advanced_learner` request bodies | 28.183s, 0.298s, 0.200s | Same guest answer; request-body persona is ignored |
| 93:3 | guest default | 16.949s | Context-first summary and a verse-specific reflection question |
| 6:57 | deterministic-only base plan | 21.418s | Full answer, seven excerpts/five scholarly badges reported by pipeline metadata, but only Ibn Kathir in primary tafsir |
| `patience` | invalid verse query | pre-generation 200 clarification | Generic verse-format help and examples unrelated to patience |

### What is already helping users

- The picker covers all 114 surahs and includes a large curated bank of meaningful quick selections (`frontend/app/components/SurahVersePicker.jsx:5-285`). The daily verse gives a low-friction starting point (`frontend/app/page.js:1787-1813`).
- Arabic is rendered RTL in a dedicated Amiri font with generous responsive sizing and line height (`frontend/app/globals.css:1166-1177`). Related verses are actionable, not decorative (`frontend/app/page.js:2993-3038`).
- Live 93:3 first located the reassurance in the pause of revelation, then invited personal application. Live 1:5 asked about making repeated recitation conscious and transformative. These are materially better than a generic “How does this apply?” prompt.
- The scholarly-source service constrains the model to supplied excerpts and has deterministic routing fallback (`backend/services/source_service.py:1553-1695`), a sound foundation for evidence-bounded generation.
- Reduced-motion and focus-visible CSS already exist (`frontend/app/globals.css:1857-1873`), so the accessibility work is targeted rather than a ground-up rebuild.

## Ranked findings

### 1. P0 — Hadith attribution can combine material that is not in the cited collection

- **User problem:** A learner may treat a generated composite as a verbatim, authenticated hadith from Sahih Muslim. That can misteach sacred material and makes every other citation harder to trust.
- **Evidence:** The live 2:255 answer labeled its first item “Sahih Muslim, narrated by Ubayy bin Ka'b” and included an added statement that the verse has a tongue and lips. [Sahih Muslim 810](https://sunnah.com/muslim:810) does not contain that addition. The app's own source tradition, [Ibn Kathir on 2:255](https://previous.quran.com/2%3A255/tafsirs/en-tafisr-ibn-kathir?locale=en), distinguishes the versions: Ahmad records the longer wording, while Muslim collected the report without that addition. The prompt only asks for a free-form `reference`, `text`, and `relevance`; it does not require a canonical locator, grade, or source pointer (`backend/app.py:3699-3704`).
- **Proposed change:** Make hadith a retrieval-and-validation field, not a free generation field. Require `collection`, canonical ID, grade, exact retrieved excerpt, and internal source pointer. Before caching or rendering, verify that the excerpt is contained in the cited record; otherwise drop it and log a correctness event. Keep commentary from Ibn Kathir separate from hadith text, and audit/invalidate cached responses containing unverified hadith after the fix. Add golden tests for 2:255 and other high-traffic verses. This will require a pipeline-version bump when implemented.
- **Effort:** M.
- **Expected user impact:** Critical. It prevents confident religious misattribution and establishes a trustworthy citation contract.

### 2. Guests do not see the reflection question the backend already generated

- **User problem:** A guest can read an explanation but is denied the exact moment that turns reading into tadabbur. This weakens the product before the three-query sign-up nudge has earned trust.
- **Evidence:** The results UI renders `reflection_prompt` only when `user` is truthy (`frontend/app/page.js:3080-3131`). The guest API response already contains the question, and the live prompts for 1:5 and 93:3 were specific and useful. Guest defaults are intentionally supported in the backend (`backend/app.py:6890-6898`).
- **Proposed change:** Show the reflection question to everyone. Keep durable journaling/authenticated annotations behind sign-in, but let a guest read the question and optionally copy it or write in an ephemeral local field. Phrase the sign-up CTA as saving the reflection, not unlocking the ability to reflect.
- **Effort:** S.
- **Expected user impact:** Very high. It exposes the product's north-star action on the first visit with no generation cost or prompt change.

### 3. Popular cached verses do not count toward explored-verse progress or badges

- **User problem:** A signed-in learner who studies a popular cached verse can see no progress, while a rarer uncached verse counts. Progress becomes arbitrary and discouraging precisely on likely first readings such as Al-Fatihah and Ayat al-Kursi.
- **Evidence:** Every Firestore or memory cache hit returns at `backend/app.py:6904-6935`. `_track_explored_verse` and badge checks occur only after fresh-response cache writes at `backend/app.py:7211-7224`. The learning event is therefore coupled to generation rather than study.
- **Proposed change:** Move a small idempotent `record_study_event` step onto every successful authenticated response path, after verse normalization but independent of cache status. Use a per-user/per-verse/day key so repeats are safe. Add a regression test that the same verse produces identical progress behavior on miss and hit.
- **Effort:** S.
- **Expected user impact:** High. Progress and badges become credible measures of what was studied rather than what happened to miss cache.

### 4. Anyone can publish unverified tafsir content under Tadabbur's shared-page presentation

- **User problem:** A malicious or mistaken client can create a branded share page containing fabricated verse commentary. Even without executable script, a shared link can make invented scholarship look like a Tadabbur answer.
- **Evidence:** Unauthenticated `POST /share` accepts and stores the caller's entire `response` dictionary without validating it against a server-generated/cache record (`backend/app.py:7551-7587`). The public page renders stored explanation content with raw HTML enabled (`frontend/app/shared/[id]/page.js:158-170`). This is the trust consequence behind the stored-content issue already flagged in `docs/AUDIT-2026-08-01.md`.
- **Proposed change:** Let the server create shares only from a verified response ID/cache key and store an immutable snapshot plus pipeline/source version. If client snapshots must remain, enforce a strict schema, sanitize Markdown/HTML, validate verse text against canonical data, rate-limit creation, and clearly label user-authored material. Do not accept arbitrary source names or Qur'an text.
- **Effort:** M.
- **Expected user impact:** High. Shared learning remains attributable to the product's verified pipeline instead of becoming a misinformation surface.

### 5. Source coverage degrades silently, and the plan inventory cannot currently be trusted

- **User problem:** A learner cannot tell whether an answer reflects both promised classical tafsirs, a single tafsir, or broad thematic excerpts. Absence looks like completeness, so the user cannot calibrate confidence or seek another source.
- **Evidence:** Al-Qurtubi coverage ends at 4:22 (`backend/app.py:7257-7260`). The prompt instructs the model to emit an unavailable message beyond that boundary (`backend/app.py:3681-3688`), then `filter_unavailable_sources` removes it (`backend/app.py:2229-2298`). The frontend destructures `scholarly_sources` but never renders it (`frontend/app/page.js:2797-2806`). Live 6:57 returned a rich full response and reported seven excerpts/five additional-source badges, yet its visible primary tafsir was only Ibn Kathir and there was no coverage notice. Even 1:5 returned only Ibn Kathir in this probe despite being within nominal Qurtubi coverage. Separately, `_metadata` in `_precomputed_scholarly_plans.json` disagrees with the file's actual 6,236 entries and origin counts.
- **Proposed change:** Add an explicit, deterministic coverage object before generation: availability for each classical tafsir, additional sources actually retrieved, match method (`verse_plan`, `keyword`, `surah_overview`), and any limitation. Render a compact “Sources used for this answer” panel and a neutral “Al-Qurtubi is not available in this corpus for this verse” notice. Regenerate metadata from the file in CI and distinguish Gemini-origin, deterministic-base, and runtime-fallback plans. Rename `_scholarly_pipeline` labels so deterministic-only plans are not called simply “precomputed.” A response-shape change requires a pipeline-version bump.
- **Effort:** M.
- **Expected user impact:** High. Users can see what an answer is based on, understand gaps without losing the answer, and decide when to consult another tafsir.

#### The requested uncovered-verse test, corrected

There is no current verse key with no plan object. For 6:57, the stored base plan is deterministic-only: Asbab al-Nuzul plus the surah thematic overview, with reasoning that no topical keyword matched. At runtime, `plan_scholarly_retrieval_deterministic` merges keyword and verse-map pointers (`backend/services/source_service.py:1568-1613`), so the live user received the Arabic/translation, Ibn Kathir explanation, summary, cross-references, hadith/lessons, and pipeline metadata reporting seven excerpts across five additional source types. The user did **not** receive al-Qurtubi or a visible explanation of why, did not see the scholarly badges in the UI, and as a guest would not see the generated reflection question. This is graceful technical fallback but poor coverage communication.

### 6. The product computes a next-reading path but loses it before users can use it

- **User problem:** After learning one verse, the user has no prominent, reasoned “continue here” path. Related verses help, but there is no coherent next step tied to a theme, plan, or learning history.
- **Evidence:** `_generate_recommendations` exists (`backend/app.py:5555-5619`) but is added only after both memory and Firestore cache writes (`backend/app.py:7211-7225`); cache hits return earlier, so cached responses do not contain it. `frontend/app/components/RecommendationBar.jsx` is orphaned and never imported. The current UI does render clickable cross-references, which is a useful partial path, not a full personalized recommendation loop.
- **Proposed change:** Compute deterministic recommendations before cache storage or attach them consistently on every response path. Render two or three “Continue reflecting” cards with verse, reason, and estimated reading scope; always include one direct textual cross-reference and optionally one theme/plan step. Measure click-through followed by a completed read/reflection, not card impressions alone.
- **Effort:** M.
- **Expected user impact:** High. A one-off answer becomes a guided learning sequence without requiring a new model call.

### 7. The app cannot yet explain where the 17–28 seconds are spent

- **User problem:** Latency work will be guesswork, so engineering may optimize a cheap stage while users still wait on the real bottleneck.
- **Evidence:** `perf_metrics` is initialized and populated (`backend/app.py:6749-6759`, `6768`, `6899`, `6908-6936`) but never attached to a response or structured telemetry. All live responses omitted it. Observed long-path times were 16.475s, 28.183s, 16.949s, and 21.418s; warm repeats were 0.200–0.491s. There is no response cache-status marker, so even that split cannot be classified confidently.
- **Proposed change:** Emit a `Server-Timing` header and a cache-status header (`hit-firestore`, `hit-memory`, `miss`) on every path, plus structured server logs for retrieval, prompt build, Gemini, extraction, post-processing, and cache write. Keep internal detail out of the persisted answer object. Establish p50/p95 by cache status before changing infrastructure.
- **Effort:** S.
- **Expected user impact:** Medium-high indirectly. It makes the next performance change measurable and prevents spending money on an unverified fix.

### 8. Cold-path users see only a spinner until the full commentary is complete

- **User problem:** For 17–28 seconds, the learner cannot begin reading even though the canonical verse and translation are much cheaper to retrieve than the generated tafsir.
- **Evidence:** The loading UI is a spinner and “Preparing your reflection...” (`frontend/app/page.js:1901-1909`). A `TafsirSkeleton` exists but is not used for this request. The public verse endpoint can return the verse independently (`backend/app.py:6542-6557`). The main response is one large JSON object, so streaming it would require a more invasive protocol/cache change.
- **Proposed change:** On selection, fetch/display Arabic, translation, and verse reference immediately while `/tafsir` runs in parallel. Use the existing skeleton for explanation sections, announce meaningful states (“Verse loaded; gathering classical commentary”), and retain cancel/retry. First measure this approach. Consider full generation streaming only later; strict structured JSON and permanent caching make it a larger, riskier first move.
- **Effort:** M.
- **Expected user impact:** High. Time-to-first-insight becomes the verse-fetch time instead of the generation time, and users can start tadabbur while deeper material arrives.

### 9. Persona adaptation changes instructions, but not enough of the learning experience

- **User problem:** A new learner can still receive a dense academic synthesis, while an advanced learner gets almost the same sequence and length with harder vocabulary. “Personalized” risks meaning lexical substitution rather than better teaching.
- **Evidence:** All five persona configs use `academic_prose` (`backend/app.py:220-260`). The prompt varies tone, vocabulary, hadith, and debate flags (`backend/app.py:3513-3524`) but mandates the same paragraphs, exactly two tafsir slots, a 4–6 sentence scholarly synthesis, and exactly three fixed lessons for everyone (`backend/app.py:3618-3648`, `3657-3668`, `3707-3731`, `3748-3762`). Public `/tafsir` ignores request-body `persona` and gives guests `curious_explorer/beginner` (`backend/app.py:6763-6767`, `6890-6898`), so the three requested 1:5 persona probes all exercised the same guest profile. This does **not** prove authenticated profiles are identical; it proves the proposed public comparison cannot test them and the prompt structurally compresses their differences.
- **Proposed change:** Define persona contracts around learning needs and regression-test them with authenticated/internal fixtures: new revert = meaning first, explain every Arabic term, one action, no debate; curious explorer = context plus one open question; practicing Muslim = worship/character application; student = named positions and source locators; advanced = Arabic rhetoric, disagreements, evidence strength, and uncertainty. Let depth, section count, and optional hadith differ; keep only the canonical verse/source schema stable.
- **Effort:** M.
- **Expected user impact:** High. Each reader receives the right cognitive load and a clearer bridge from meaning to practice.

#### Prompt before/after examples

These are target behaviors for prompt tests, not replacement tafsir and not production copy.

| Verse | Current tendency observed | Better meaning-first opening | Better reflection prompt |
|---|---|---|---|
| 1:5 | Opens with an academic definition of tawhid, then a fixed three-stage progression | “Worship belongs to Allah alone, and even our ability to worship depends on asking Him for help.” Advanced mode can then explain the fronting of *iyyaka* with attribution. | “Where are you trying to carry something as if it depends only on you? What would asking Allah for help—and then taking the next responsible step—look like today?” |
| 2:255 | Uses broad theological exposition and introduced an unverified composite hadith | “Allah's care never lapses: He does not tire or sleep, so creation is never outside His knowledge and guardianship.” Then layer al-Hayy, al-Qayyum, intercession, and the Kursi according to level and evidence. | “Which worry are you carrying as though everything depends on your vigilance? What can you responsibly do, then entrust to the One who never sleeps?” |
| 93:3 | Correctly gives the revelation-pause context, then moves quickly to universal reassurance | “This verse first reassures the Prophet during a pause in revelation: delay was not abandonment.” Clearly label the later personal application as reflection, not the verse's historical addressee. | “When silence feels like rejection, what evidence of Allah's past care can keep a feeling from becoming a verdict?” |

For all personas, make the first two sentences answer “What does this verse mean here?” before scholarly layering. Generate a reflection question from a verse-specific tension, image, command, or contrast; do not force Shariah/Tariqah/Haqiqah progression when the source material does not naturally support it.

### 10. A learner who starts with a life question cannot ask by topic

- **User problem:** Many first-time users know the concern—patience, grief, forgiveness—but not a verse reference. The shipped experience assumes prior Qur'an navigation knowledge.
- **Evidence:** The main form is hidden and accepts only the picker output (`frontend/app/page.js:1877-1893`). The picker offers three randomized quick choices plus unlabeled surah/from/to selects (`frontend/app/components/SurahVersePicker.jsx:424-523`). Directly posting `patience` returns a successful clarification response whose examples are generic formatting examples such as 2:255, not patience suggestions (`backend/app.py:6783-6841`). Non-tafsir approaches are normalized back to tafsir (`backend/app.py:6777-6780`).
- **Proposed change:** Add a distinct “Explore a theme” entry point. Start safely with curated theme chips backed by the existing quick-select catalog and show that these are editorial suggestions. If free-text semantic discovery is added, return ranked canonical verses with a reason and let the user choose before generating tafsir; do not send an arbitrary life question straight to a religious answer generator.
- **Effort:** M for the proposed curated theme path. Trustworthy free-text retrieval is a later L project.
- **Expected user impact:** High. Users can begin from the question they actually have while retaining transparent, verse-first grounding.

### 11. Core controls and changing states are not fully named for assistive technology

- **User problem:** A keyboard or screen-reader user may not know what the three selects control or when a long answer has arrived. Arabic may be pronounced with the page's English language context.
- **Evidence:** The surah/start/end selects have placeholder options but no `<label>` or accessible name (`frontend/app/components/SurahVersePicker.jsx:467-523`). The loading block has no `role="status"`/live region (`frontend/app/page.js:1901-1909`), and the normal results container is not announced. Arabic text uses `dir="rtl"` but not `lang="ar"` (`frontend/app/page.js:2937-2942`; shared page `frontend/app/shared/[id]/page.js:147-149`). Positive baseline: Amiri, responsive sizing, RTL, reduced motion, and focus-visible styling already exist.
- **Proposed change:** Add visible labels or `aria-label`s to picker controls, group range controls with a fieldset/legend, make loading and completion polite live regions, put `lang="ar" dir="rtl"` on Arabic, and run a keyboard + VoiceOver/NVDA pass at mobile width. Test focus after auto-submit and after errors.
- **Effort:** S.
- **Expected user impact:** Medium-high. The core study path becomes understandable without sight or a pointer, with minimal visual change.

### 12. Streaks primarily reward query success, not demonstrated reflection

- **User problem:** A user can grow a streak by opening an answer without reading or reflecting, while meaningful guest reflection is not available. The mechanic trains clicks more reliably than understanding.
- **Evidence:** The frontend calls `updateStreak()` after every successful signed-in tafsir response (`frontend/app/page.js:1305-1318`). Backend badges mix useful study/reflection achievements with search-driven streak and exploration counts (`backend/app.py:4921-5516`). The three-query guest nudge emphasizes saved progress, streaks, reflections, and plans, but the guest reflection UI is hidden.
- **Proposed change:** Keep a gentle “showed up today” streak, but add a separate study-quality signal: answer viewed for a reasonable interval, one related verse opened, a reflection started/saved, or a plan step completed. Never require journal content or score spirituality. Show progress as “verses studied” and “reflections revisited,” with streaks secondary.
- **Effort:** M.
- **Expected user impact:** Medium. Motivation becomes better aligned with sustained learning while avoiding manipulative or spiritually presumptive scoring.

### 13. Response budget and cache strategy are not tied to observed tails

- **User problem:** The app may pay for and wait on an output ceiling far above normal answers, while popular-content prewarming and cold-instance decisions are made without cache/latency evidence.
- **Evidence:** Main generation permits `maxOutputTokens: 65536` (`backend/app.py:7095-7103`). Warm repeats were sub-0.5s, demonstrating the value of cache, but the absence of cache/timing headers prevents attribution. The backend deploy sets max instances but no minimum instance (`deploy-backend.sh:51-54`), so a prewarmed Firestore answer and a warm Cloud Run instance solve different delays.
- **Proposed change:** After finding #7, record output-token p95 by verse-range/persona and run a golden-set regression at a lower cap (for example 8K/16K, chosen from data, not assumption). Use the secured prewarm endpoint for a reviewed list of high-read guest-default verses and verify cache keys. Treat `min-instances` as a separate Ahmed billing decision only if measured cold-start latency justifies it. Do not use streaming or prewarming as a substitute for showing the verse immediately.
- **Effort:** S for the proposed measurement and cap experiment. A recurring prewarm program is a later M operational task.
- **Expected user impact:** Medium. Safer tail latency and cost create room for more learning without risking truncated answers.

### 14. Remaining reliability debt should be prioritized by user interruption, not cleanup volume

- **User problem:** A corrupted local onboarding record can break first-run state, and an unset cron secret leaves a cost/email endpoint callable. Broad cleanup matters less than these concrete interruptions and trust boundaries.
- **Evidence:** `JSON.parse` of onboarding localStorage is unguarded (`frontend/app/hooks/useOnboarding.js:31-42`). `/feedback/daily-summary` authenticates only when `FEEDBACK_CRON_SECRET` happens to be configured (`backend/app.py:10166-10178`). `docs/AUDIT-2026-08-01.md` also inventories dead semantic/vector paths, duplicate frontend API layers, CORS duplication, and configuration sprawl; most are maintenance risks rather than immediate learning gains. P2 already contains build/dependency/iOS fixes and the October model migration, so those should not be rediscovered as product features.
- **Proposed change:** Fail closed on the cron secret, catch/reset invalid onboarding state, and add route-level error boundaries for the study path. Then perform dead-code/config cleanup in isolated PRs with route/build traces. Keep model migration on its existing deadline and golden-response plan. Do not let the monolith refactor displace the higher-ranked trust, reflection, coverage, and latency work.
- **Effort:** M as a small reliability batch plus separate cleanup PRs.
- **Expected user impact:** Medium. Fewer first-run failures and a smaller abuse surface, while engineering effort stays focused on learning outcomes.

## Recommended promotion order

1. Stop and quarantine unverified hadith citations; add the 2:255 golden test and audit affected cache records.
2. Ship the three small behavioral fixes together only if review scope remains clear: guest reflection visibility, cache-hit study tracking, and timing/cache headers.
3. Define and implement the source-coverage contract, including regenerated plan metadata and UI source badges.
4. Add verse-first progressive loading, then evaluate measured token cap/prewarm changes.
5. Design the persona regression matrix and next-reading cards as one learning-quality batch.
6. Treat trustworthy topic discovery as a product/retrieval project, not a prompt toggle.

No proposal above has been implemented in this review. Claude should validate the religious-source remediation and architecture implications; Ahmed should prioritize, approve any billing/cache operations, and promote chosen items into `HANDOFF.md`.
