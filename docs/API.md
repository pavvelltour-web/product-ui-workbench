# Advanced CLI reference

Normal skill use is described in [USAGE.md](USAGE.md). The helpers below are optional evidence tools, not a design generator or proof that an agent actually viewed a source.

## Public package maintenance

The root `SKILL.md`, `references`, `scripts` and `library` form one self-contained skill. Keep private run data outside this repository. After reviewed source changes, refresh the byte inventory and validate the package:

```bash
python scripts/inventory.py
python scripts/check_public.py
python -m unittest discover -s tests -v
python scripts/package.py --out ../product-ui-workbench.zip
```

`inventory.py` creates new expected hashes; it is not a way to verify an untrusted download. Packaging and installation require an exact allowlisted file set and matching hashes. They exclude Git metadata, private runs and environments. Existing installation/archive paths are preserved. `.gitattributes` keeps distributed text bytes stable across platforms. Browser tests need the optional runtime described in [DEPENDENCIES.md](DEPENDENCIES.md); a skipped test is not a pass.

## Built app closure and actual renderer

For React/Vite or any multi-file static build, first copy built `dist` into a run-owned `generated/<variant>-<iteration>-dist/` folder. Never render/register an entry alone as if its imports were preserved. Create a workspace-relative source manifest:
```json
{"root":"generated/demo-1-dist","entry":"index.html","ownership":"run-transient","files":[{"path":"index.html","sha256":"exact hash"},{"path":"assets/index-EXACT.js","sha256":"exact hash"},{"path":"assets/index-EXACT.css","sha256":"exact hash"}]}
```
Every file below `root` must be listed exactly once with its actual SHA-256; `entry` and each `path` are relative to that root. New/missing/changed files invalidate review. Symlinks/reparse points, traversal and unsafe paths fail closed. Use `ownership:"active"` for an explicitly retained app/build: export works, cleanup preserves it. `run-transient` is accepted only below `generated/` or `transient/`; old single-file registration remains supported and protects files outside those run-owned locations.

Capture through the real optional browser dependency, already-installed Python Playwright and an explicitly named installed Chrome executable:
```
python scripts/render_web.py --workspace <runs-folder> --source-manifest inputs/demo-1-closure.json --chrome <absolute-Chrome.exe> --out images/demo-1 --query "variant=demo" --full-page
```
Output: `images/demo-1/desktop.png` (viewport1440×1000), `mobile.png` (viewport390×844), `capture.json`. Defaults are viewport crops; add `--full-page` for both full scroll heights, or `--mobile-full-page` for desktop viewport + mobile full page. Each screenshot records its own full-page flag and dimensions. The server binds only127.0.0.1 on an ephemeral port, serves only closure-listed files and blocks external requests. Any network/runtime/console failure, horizontal overflow or empty/unreadable render fails the capture gate. This is render evidence, not task behavior testing or pixel judgment. Renderer requires Playwright explicitly; CLI bookkeeping remains standard library only.

Register with the existing command plus optional manifest:
```
python scripts/pipeline.py --workspace <runs-folder> render --campaign crm --variant demo --iteration 1 --source generated/demo-1-dist/index.html --source-manifest inputs/demo-1-closure.json --capture-record images/demo-1/capture.json --view-query "variant=demo" --png images/demo-1/desktop.png images/demo-1/mobile.png --generator "actual external agent/run"
```
Review hashes still pin the entry/PNGs; the render record also pins the full closure and source-manifest hash. `export` now copies the full verified closure to `exports/<campaign>/<variant>/<iteration>/app/` and returns its actual entry and file hashes. Serve that `app/` root for Vite absolute `/assets` links. It does not copy package manager dependencies, development source or the active application.

Use `--query "variant=demo"` for an app view selected by URL parameters. Strict parsing/re-encoding keeps the host/path fixed; omit it for an app with one entry view. The capture records its normalized `view_query` and actual local `render_url`. `render --capture-record ...` verifies/pins actual successful capture, exact closure and ordered PNGs; `--view-query` must match it when explicitly supplied. Export evidence includes `view_query` and `entry_url`; preserve the query when opening the exported app. Query metadata is part of the captured view, not a separate generated app. Default viewport vs `--full-page` is explicit in capture evidence.

To create the closure manifest with actual file hashes: `pipeline.py --workspace <run> source-manifest --source-root generated/demo-1-dist --entry index.html --ownership run-transient --out inputs/demo-1-closure.json`. This inventories the existing build; it does not build/generate the app.

`cleanup` deletes only hash-matched registered run-owned source/build files, `images/` PNGs and `references/` images (or files beneath `transient/`). Active closure files, unregistered assets and any file outside those prefixes remain untouched. Winner export and all reviews are still required.

Reference assets may be PNG or JPEG: format signatures, dimensions and structural integrity are checked; JPEG inspection is a marker/header check, not a full visual decode. Actual viewing remains mandatory. Mobbin search receipt handling is documented in [tool receipts](tool-receipts.md).

## Small reusable library

`pipeline.py --workspace <run> library-search "queue detail" --job review-records --platform touch --stack react-shadcn --type pattern` returns matching typed entries, source/license hashes, composition IDs, original examples and honest verification statuses. Exact facets: `--job`, `--platform`, `--entity`, `--action`, `--density`, `--state`, `--accessibility`, `--stack`, `--type`; query ranking is deterministic token overlap with an ID tie-break. `--limit` is1..50. No embeddings, network or automatic dependencies.

The starter includes native helpers, retained shadcn/Radix TSX snapshots with separate notices and API/dependency metadata, original job patterns and synthetic source examples. `library/manifest.json` is the source of truth for current entries. Source integrity is checked; each consuming application still needs its own build, interaction and visual verification.

## Audited factual correction

If a coordinator brief contains a demonstrable factual transcription error, preserve the original source and task rather than editing campaign.json directly:
```
pipeline.py --workspace <run> task-amend --campaign crm --task inputs/corrected-task.json --reason "Exact original fixture arrays imply corrected weekly totals; brief contained arithmetic transcription error; source unchanged" --author "actual named coordinator"
```
It retains full original task/hash, append-only old/new snapshots, reason/author/time and chained record hashes. It does not reset budgets or rewrite old prompts/reviews. Prior task-dependent review/decide/export is stale for current approval; next `compile` may read the genuinely reviewed prior critique as historical under the valid amendment ledger and uses the corrected task/revision/hash. Cleanup can inspect historical reviewed transients, while winner export requires a current task revision. Unlogged task mutation or a changed amendment chain fails closed. This records a authorized correction; it does not infer permission to broaden product scope or manufacture facts.

If actual old source/pixels were rendered/inspected but the review was rejected before the correction (for example, failure accidentally marked best_so_far), use `review ... --historical-task` with the corrected truthful review input. Only a genuine older prompt under the valid amendment ledger is admitted; source/closure/capture/reference/PNG freshness still applies, best_so_far must be false and human acceptance cannot be accepted. It records historical-only critique and leaves selection unchanged. Old decide/export remain stale; next compile can use those real findings. This is recovery of missing evidence, not a bypass or retroactive approval.

Invoke `python <plugin>/scripts/pipeline.py --workspace <existing run folder> COMMAND`. All input/output paths below are relative to that workspace. Nothing is installed. This CLI validates and records evidence; the agent generates source and captures/inspects pixels externally.

1. `create --task task.json --campaign crm --iterations 3 --variants 2`
2. `reference --campaign crm --analysis reference.json`
3. `compile --campaign crm --variant editorial --reference ref-editorial --spec prompt-spec.json`
4. Read `campaigns/crm/editorial/1/prompt.md`; generate source, capture actual desktop/mobile PNGs.
5. `render --campaign crm --variant editorial --iteration 1 --source generated/editorial-1.html --png images/editorial-1-desktop.png images/editorial-1-mobile.png --generator "external agent; model/run identifier"`
6. Inspect actual PNGs; `review --campaign crm --variant editorial --iteration 1 --record review.json`
7. `decide --campaign crm --variant editorial --iteration 1`
8. Repeat compile/render/review up to each variant's limit. `export --campaign crm --variant editorial --iteration 3` copies chosen candidate source and pixels into `exports/`. `cleanup --campaign crm` deletes only tracked transient source/reference/PNG files inside the workspace after all registered renders are reviewed and each variant's best-so-far is exported and verified; retains lightweight audit records/tombstones. Export the winners only; superseded iterations need reviews, not redundant exports.

Task example:
```json
{"job":"Review CRM pipeline and open a deal", "factual_data":["Synthetic fixtures; preserve exact values"],"interactions":["Filter deals", "Open deal detail", "Close detail returns focus"],"constraints":["Responsive desktop and mobile", "No network"],"scope":"Representative CRM screen"}
```

Observed reference analysis (hash the exact viewed file; do not invent rights evidence):
```json
{"id":"ref-editorial","canonical_url":"https://example.org/exact-reference","asset_path":"references/editorial.png","asset_sha256":"64 lowercase hex characters","observed":{"observer":"agent identity","at":"2026-10-14T02:00:00Z","method":"actual-image-view"},"rights":{"purpose":"visual-analysis","status":"permitted","evidence":"Actual terms/source and authorized use boundary"},"traits":[{"id":"composition","aspect":"composition","basis":"observed","description":"Tall left navigation; large title above compact data rows"},{"id":"type","aspect":"typography","basis":"inferred","description":"Sans face; exact font unknown"},{"id":"space","aspect":"spacing","basis":"observed","description":"Wide outer margin, tight row rhythm"},{"id":"material","aspect":"material","basis":"observed","description":"Flat surfaces with fine dividers"},{"id":"color","aspect":"color","basis":"observed","description":"Warm white field with dark text"},{"id":"responsive","aspect":"responsive","basis":"proposed","description":"Stack summary above rows below 760px; static reference does not prove mobile"}]}
```

Prompt spec:
```json
{"intent":"Editorial CRM with a strong summary anchor","directives":[{"trait_id":"composition","basis":"proposed","decision":"Use 220px left navigation and a 56px heading above a seven-column deal table"},{"trait_id":"type","basis":"proposed","decision":"Use system sans with 56/18/14/12px hierarchy and tabular numeric values"},{"trait_id":"space","basis":"proposed","decision":"32px outer gutters, 48px section gap, 52px table rows"},{"trait_id":"material","basis":"proposed","decision":"Flat off-white canvas; 1px gray table rules; no card grid"},{"trait_id":"color","basis":"proposed","decision":"Charcoal #20231f on ivory #f4f4ed; green #496448 selection"},{"trait_id":"responsive","basis":"proposed","decision":"Below 760px replace side rail with top navigation and rows with deal summaries"}],"delta_findings":[]}
```
Every prompt must cover composition, typography, spacing, material, color and responsive behavior. Subsequent prompts cite previous review finding ids in `delta_findings`; a reference replacement still cites the preceding concrete critique.

Review (copy source/PNG hashes printed by render; one actual observation for each PNG):
```json
{"observer":"agent identity","inspected_at":"2026-10-14T02:10:00Z","source_sha256":"exact render source hash","png_sha256s":["exact desktop hash","exact mobile hash"],"pixel_observations":[{"png_sha256":"exact desktop hash","observation":"Observed title/table relationship and reference alignment; state concrete defects"},{"png_sha256":"exact mobile hash","observation":"Observed mobile stacking and legibility"}],"technical":{"status":"pass","evidence":"Actual interaction/build checks and their limits"},"visual":{"status":"revise","evidence":"Actual pixel comparison to the reference traits"},"human":{"status":"not-run","evidence":"No user choice received"},"independent":{"technical":"not-run","visual":"not-run","evidence":"No independent review performed"},"findings":[{"id":"title-too-small","category":"visual","severity":"major","evidence":"Desktop title is visually subordinate to summary metric","action":"Increase title and reduce metric weight"}],"best_so_far":true,"replace_reference":false}
```

Statuses: technical `pass|fail|not-run`; visual `candidate|revise|not-run`; human `accepted|rejected|not-run`; independent technical/visual `pass|fail|not-run`. A `candidate` is not human acceptance. Review evidence is an attestation by the named reviewer, not computer vision or automatic proof. Changed source/reference/pixels invalidate dependent records. A missing/evicted reference cannot be freshly reinspected; cleanup makes that boundary explicit.

Export is a final-selection step: only `best_so_far` can export, and an earlier iteration export blocks another export until explicitly reconciled. Choose after the planned comparisons. Shared artifacts in other campaigns block cleanup even when Unicode or relative aliases differ. Changing the task contract invalidates earlier reviews. PNG validation currently supports standard non-interlaced PNGs up to 128 MiB of decoded scanlines.

The legacy `render --source` path pins only its named file and is suitable for genuinely self-contained HTML. For a built app, use the implemented `source-manifest` and `render --source-manifest --capture-record` route: it pins every HTML/CSS/JS/imported asset, records the actual selected view, and exports the complete runnable static closure. The renderer supplies deterministic web MIME types for JavaScript modules, including `.mjs`, independently of Windows file associations. Development source, dependencies and build commands remain explicit external inputs; the package does not install or build a project automatically.


## Design-only route (0.6.0)

No job/actor/brand/backend prerequisite. Write viewed analysis, a contextual normalized `pattern_loop` packet and a concrete reconstruction prompt. Run `design_loop.py --workspace ROOT prepare --id study --analysis analysis.json --patterns patterns.json --prompt prompt.md --source-root generated/study --out runs/study.json --budget 2`, then `attach-references --ledger runs/study.json --packet packet.json` before source binding. `bind-source --ledger ... --source ...` binds actual generated files, refusing missing/stale references and source predating the prepared prompt.

Review input includes named observer, viewed PNG pins, six design dimensions and `artifacts` mapping calibration/study/components to actual `render_web.py` capture.json pins. Each capture must match study/mode, passed checks, source-manifest hash and complete current static closure. Declared PNGs must come from these captures. `calibration_comparison` names source IDs, region, status, actual difference evidence and intentional adaptations. A final candidate requires all three artifact kinds and successful calibration transfer. Source observation is still external attestation, not automatic computer vision.

A subsequent source binding chains the previous review/directive. To change the prompt, `revise-prompt --ledger ... --prompt new-version.md --findings reference-fidelity --module geometry --expected 'observable difference'` keeps previous pins and the same total iteration budget. `amend-evidence` is only a named, recorded correction of analysis/pattern evidence before first binding; it cannot replace a pinned prompt or reset a budget.


## Contextual UX gate (0.7.0)

`design_loop.py prepare` accepts `--ux-plan UX-PLAN.json`, validated by `ux_contract.py` and pinned before generated source. Old no-plan callers retain their existing behavior; the current skill requires a plan for new operational/catalog studies. Validate a proposal alone with `ux_contract.py --workspace ROOT --plan UX-PLAN.json --study-id STUDY`. Use `docs/ux-plan.example.json` for the exact shape. `intent.basis` is `supplied|proposed`; no actor/backend/brand contract is required. A leading KPI is allowed when the plan explains its purpose and reading/action decision. Declared grouping/type/control/chart/mobile relationships are context-specific proposals.

For a plan-bearing ledger, review JSON additionally includes `"ux_evidence":{"path":"reviews/ux.json","sha256":"actual hash"}`. The UX file follows `docs/ux-evidence.example.json`: version1.0, matching study/plan SHA, named observer, pending human acceptance, exact same artifact pins as the visual review, all distinct current capture source-manifest pins, and viewed current PNG pins including desktop/mobile study. The existing artifact validator first checks capture pass/mode/study, exact current source closure and PNG membership. The UX gate then checks that its declarations refer to those same current records. A file claiming a measurement needs selector, viewport, name, value and unit; this remains an observer attestation, not a measurement engine.

`criteria` must contain exactly `attention-priority`, `semantic-grouping`, `type-roles`, `chart-semantics`, `control-coherence`, `scope-and-selection`, `detail-hierarchy`, `touch-first-useful`. Each records status `pass|revise|not-run`, method `image-observation|measured-dom|mixed`, concrete evidence and `capture_sha256s` identifying viewed current PNGs. The latter two methods require nonempty `measurements`. Attention priority requires image judgment (`image-observation|mixed`) and cannot pass via a numeric score alone. An inapplicable chart/detail needs observed absence and the stated reason. `candidate` requires every UX criterion pass in addition to the original six visual dimensions; no human acceptance is inferred. Revision/stop-budget records retain unresolved UX findings. `revise-prompt --findings` accepts these UX IDs while retaining the same total budget and previous review pin. The pinned UX plan cannot be silently amended after failure; a genuinely changed authorized intent uses a separately identified study with old evidence retained.

Compatibility boundary: optional CLI plan support does not upgrade historical reviews or assert that old variants passed these new UX checks. Source/PNG freshness and schema completeness do not establish that an observer looked, that the declared measurement is correct, that people can use the design, or that a user likes it.

## Declared actual browser interactions (0.8.0)

UX plan version1.0 accepts an optional `interaction_checks` array for CLI compatibility. The current skill requires a nonempty meaningful array for new operational/catalog studies. Every check has a unique `id`, `kind`, CSS `target` and `viewports:["desktop","mobile"]`. `kind:"selected-value-visible"` reads the actual closed value target. `kind:"open-region"` additionally requires a direct CSS `trigger`, visible text `identity`, `close:"Escape"` and `focus_return:true`. See [the guide](../references/render-review.md) and [plan template](ux-plan.example.json).

```
python scripts/browser_probe.py --workspace ROOT --source-manifest runs/build-1-manifest.json --plan research/VAR/ux-plan.json --out images/VAR-interaction-1 --chrome ABSOLUTE_CHROME
```

The optional existing Playwright/Chrome runtime is the same as the renderer. No packages are installed. Exact closure-listed files are served only on localhost; external HTTP/WebSockets are blocked. Each case uses a fresh context at1440×1000 or390×844. Output `interaction.json` pins plan SHA, study/query, complete current manifest and actual state PNGs, errors, text/style/geometry measurements and concrete assertions. Selected-value cases capture before/value; region cases capture before/opened/closed and check identity, Escape close and opener focus. Failed cases retain failure captures. Outputs are never overwritten.

For a native single-line `<select>`, the selected option label and actual control/content geometry are measured separately: native internal glyph rectangles are not exposed as DOM Range rectangles. Custom text targets use the DOM Range heuristic. Both routes preserve actual PNGs for viewing and remain limited text/style/geometry checks, not pixel recognition or full contrast certification. Multi-select/listbox controls need a different check rather than a closed-value assertion.

Review JSON adds `"interaction_evidence":{"path":"images/VAR-interaction-1/interaction.json","sha256":"exact hash"}` when the pinned plan contains checks. The gate rejects missing/unknown/duplicate cases, omitted touch coverage, changed check definitions, stale plan/build/PNGs, wrong study manifest, missing assertions/measurements, contradictory summaries and unresolved candidate cases. Failed structured probes can accompany revise/stop-budget reviews. They share the same existing bounded iteration ledger; no reset or automatic intent change is introduced. JSON structure is not cryptographic runner attestation. Passing declared browser slices does not establish full task coverage, correct attention hierarchy, accessibility, beauty or human acceptance.

### Frozen legacy plan selector adapter

Do not rewrite an already pinned UX plan to pretend the new selector schema was prepared before source. If that plan already declares the same interactions in controls/mobile/prompt but lacks `interaction_checks`, bind an explicit additive selector file before the first `bind-source`:

```
python scripts/design_loop.py --workspace ROOT attach-interactions --ledger runs/VAR-ledger.json --checks research/VAR/interaction-checks.json --observer "named coordinator" --basis "Selectors bind the already declared direct detail opener, Escape/focus recovery and visible Select; intent remains unchanged"
python scripts/browser_probe.py --workspace ROOT --source-manifest runs/build-1-manifest.json --plan research/VAR/ux-plan.json --checks research/VAR/interaction-checks.json --out images/VAR-interaction-1 --chrome ABSOLUTE_CHROME
```

The selector file is `{"version":"1.0","study_id":"VAR","interaction_checks":[...]}`; optional `plan_sha256` must match when present. The ledger pins it plus the unchanged UX plan SHA, named semantic basis, time, whether source already existed, and no budget reset. This is a transparent before-first-bind compatibility attachment, not a pre-source claim or an authorized intent change. Embedded checks cannot be overridden, existing bindings cannot be replaced, and attachment after first bind is rejected. The optional `--checks` probe pins that exact selector file; review requires its same contract pin and unchanged core plan/build evidence. Meaningful intent correspondence remains a named attestation and independent inspection.
