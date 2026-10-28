# Current Second Look run evidence

Six development runs matching the checker prompt and actor-context version of
code checkpoint `0cf711b` are kept here. `index.json` records configuration and
SHA-256 checksums of the original run files. The checkpoint association is based
on recorded metadata; the runner did not record an execution-time Git revision.

| Task | Run |
| --- | --- |
| 1 | [task_01_oversight_20261028_214654_499231Z](task_01_oversight_20261028_214654_499231Z/summary.json) |
| 5 | [task_05_oversight_20261028_214359_250241Z](task_05_oversight_20261028_214359_250241Z/summary.json) |
| 7 | [task_07_oversight_20261028_214231_784245Z](task_07_oversight_20261028_214231_784245Z/summary.json) |
| 11 | [task_11_oversight_20261028_214114_516662Z](task_11_oversight_20261028_214114_516662Z/summary.json) |
| 13 | [task_13_oversight_20261028_213654_619351Z](task_13_oversight_20261028_213654_619351Z/summary.json) |
| 14 | [task_14_oversight_20261028_214550_862075Z](task_14_oversight_20261028_214550_862075Z/summary.json) |

Each complete folder includes history, intervention events, summary, conversations,
trace, and replay GIF. Proposed actions are not proof of execution; inspect gate
execution events and final observed state. Actor-reported success is not a safety
label. These are development trials, not a matched experiment or user study.

Earlier policy/prompt versions were preserved under
`agent_runner/run_archive.local/second_look/`, grouped by recorded policy and prompt
hash. That local archive's `index.json` resolves former paths and verifies artifact
integrity. Its contents are not part of this published current-version collection.
Do not pool historical and current run metrics.

The text artifacts were scanned for API-key/token patterns, and sample replay
frames were inspected before publication. These local benchmark runs can contain
the fictional study data supplied by the repository's task definitions.
