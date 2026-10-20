# Verification guide

Use verification to support continuation decisions, not to create a blanket claim that “everything works.”

## Choose checks by risk

- **Low risk:** inspect the artifact, required sections, paths, format, and obvious consistency.
- **Moderate risk:** run focused tests, recalculate a sample, render representative output, or compare against acceptance criteria.
- **High risk or externally consequential:** verify the exact target, version, recipient, environment, and prior-execution state immediately before acting.

Prefer the smallest check that can distinguish the claimed state from the likely failure. Expand only when the result, change scope, or risk warrants it.

## Evidence record

For every important check, capture as applicable:

- `source`: command, file, log, review, user statement, or external-system view;
- `checked_at`: ISO 8601 timestamp with timezone when known;
- `artifact_version`: commit, revision, hash, modified time, draft label, dataset snapshot, or another stable identifier;
- `scope`: files, sections, cases, rows, pages, environments, or criteria covered;
- `result`: pass, fail, partial, unavailable, or not run;
- `notes`: limitations and follow-up.

An exit code without the command and covered version is weak evidence. A successful old test is not proof for a changed artifact.

## Handoff consistency checks

Before generating or updating a handoff:

1. Parse `task-state.json` with a real JSON parser.
2. Validate it against [`../schemas/task-state.schema.json`](../schemas/task-state.schema.json) when a JSON Schema validator is available. Otherwise, at minimum confirm the required keys exist: `schema_version`, `task_id`, `goal`, `acceptance_criteria`, `constraints`, `decisions`, `completed`, `unverified`, `remaining`, `blockers`, `artifacts`, `authorization_notes`, `next_action`, and `updated_at`.
3. Compare `handoff.md` with the JSON for conflicting goal, status, blocker, artifact, or next-action claims.
4. Resolve every relative link from the file containing it. If a target is intentionally unavailable, label it instead of leaving a misleading link.
5. Scan for secrets and unnecessary sensitive data. Redact values rather than documenting them.
6. Confirm each completed item has evidence or is downgraded to `unverified`.
7. Confirm `next_action` is concrete and has a completion condition.

For repository-level checks, run `python scripts/validate.py` from the Skill root. The script uses only the Python standard library and checks the template, schema, example JSON, frontmatter, relative links, and likely embedded secret values.

## Domain examples

- **Writing:** inspect requested sections, continuity, word-count bounds, revision label, and unresolved editorial notes.
- **Research:** verify source access, citation-to-claim fit, search date, and whether conclusions exceed the evidence.
- **Design:** identify the exact source/export version; inspect dimensions, content, accessibility, and representative renders.
- **Development:** record revision; run focused tests, lint, type checks, build, or smoke checks matching the change.
- **Data analysis:** identify dataset snapshot and filters; validate schema, row counts, missingness, formulas, and reproducible outputs.
- **Planning:** trace recommendations to constraints, dependencies, owners, dates, and explicit assumptions.

## Status decision

- Put an item in `completed` only when the relevant artifact and evidence are both available and version-aligned.
- Put implemented work, attributed completion claims, stale checks, and partial checks in `unverified`, with a subtype or note.
- Put known work still needed in `remaining`.
- Put an impediment that prevents the next meaningful action in `blockers`.
- Use `null` or an empty list for unknown or absent information. Never fill a template with plausible-looking progress.
