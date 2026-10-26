# Actual tool receipt input examples

The local adapter **does not search** and cannot authenticate an input receipt. Save the exact actual callable request/result returned by MCP and add the real viewer/source information. Examples below are contracts with placeholders, not fabricated successful tool runs. Keep private receipts inside the run; only compact original schemas/examples enter this plugin.

Run `python scripts/tool_receipt.py --workspace <run> --receipt inputs/mobbin-receipt.json --out inputs/observed-reference.json`, then pass the normalized reference to the existing `pipeline.py reference` command.

Mobbin screen receipt:
```json
{"provider":"mobbin","tool":"mcp__mobbin__search_screens","retrieved_at":"actual ISO timestamp","request":{"platform":"web","query":"Client relationship register with next actions and detail panel","limit":3,"mode":"standard","image_format":"jpg","output_destination":"code","task_intent":"Improve two original CRM workspaces using observed app screens."},"result":{"screens":["COPY ACTUAL STRUCTURED SCREEN OBJECTS"]},"selected_id":"ACTUAL RETURNED ID","expected_app":"ACTUAL DESIRED APP","id":"crm-leading-reference","asset_path":"references/selected-full-resolution.jpg","asset_sha256":"ACTUAL VIEWED FILE HASH","observed":{"observer":"actual named agent/person","at":"actual ISO timestamp","method":"actual-image-view"},"rights":{"purpose":"visual-analysis","status":"permitted","evidence":"actual purpose-specific access/use boundary; no redistribution/training permission implied"},"traits":["ACTUAL OBSERVED/INFERRED/PROPOSED TRAIT OBJECTS"]}
```
When the actual result contains `ai_usage_notice`, copy it unchanged into result and record `notice_presented_verbatim:true`, `presented_notice_text:<exact text>` **after actually presenting it separately to the user**. Its text is returned unchanged by the adapter; a boolean cannot certify that a conversation really displayed it. Flow receipts additionally specify `selected_screen_id`; viewing one frame does not establish all flow states. Keep output_destination/task_intent/output_tool identical across same-task calls. The pipeline compares destination/intent against other receipt-backed campaign references.

shadcn source/example receipt:
```json
{"provider":"shadcn","tool":"mcp__shadcn__view_items_in_registries","retrieved_at":"actual ISO timestamp","request":{"items":["@shadcn/dialog","@shadcn/table"]},"result":{"content":["COPY ACTUAL RETURNED SOURCE/EXAMPLE DATA"]},"registry":"@shadcn","registry_style":"actual resolved registry style","framework_version":"actual React/package version","files":[{"path":"component-sources/dialog.tsx","sha256":"actual file hash"}],"license_evidence":"actual upstream MIT/license notice path or source pointer","api":{"dialog":"actual controlled/uncontrolled props; keyboard/focus contract"},"local_library_gate":"not-run"}
```
The adapter retains actual source hashes/API/license fields. To set `local_library_gate:"pass"`, provide actual imports/build/task-state evidence in `build_and_task_evidence`. This field is a named human/agent attestation; tests, package metadata or component-like naming alone cannot establish library implementation quality. No add/install command is executed automatically.
