---
name: topoform
description: Create self-contained interactive diagrams from validated JSON models for architecture, workflows, data lineage, dependencies, knowledge maps, and state graphs. Includes offline assets, named views, search, filtering, and PNG export.
license: MIT
compatibility: Python 3.10+ for validation and building; no npm install or runtime network is required. Playwright and Chromium are required for browser checks. Screenshot inspection requires a visual-capable tool.
metadata:
  version: "1.0.0"
---

# Topoform

Create an inspectable diagram, not an invented architecture. Edit a small JSON
model, validate it, and reuse the bundled renderer and layout adapter. Do not
rewrite graph rendering or hand-place every node.

## Read selectively

Read [model.md](references/model.md) before authoring a model. Read
[composition.md](references/composition.md) before changing the viewer or
layout. Read [icons.md](references/icons.md) before adding icons. Consult
[quality-and-limits.md](references/quality-and-limits.md) for failures and
[sources.md](references/sources.md) for primary documentation. Do not load
vendored JavaScript into the agent context.

## Working contract

Keep these distinct:

- **Authored facts:** source JSON, stable IDs, evidence, and meaningful
  directed or undirected relationships.
- **Presentation:** node dimensions, generated positions, filters, highlights,
  colors, and icons.
- **Verification:** schema validation, real browser execution, screenshots, and
  human or agent visual review.

The JSON diagram model is the maintainable source. The generated HTML diagram
artifact is the portable deliverable. The viewer never provisions resources or
interprets a diagram as executable infrastructure.

Use arbitrary meaningful node and edge kinds. Do not assume AWS, servers,
software, or a cloud provider when the subject is a team, process, dataset, or
other system. A generic symbol is preferable to a false product logo.

## Workflow

### 1. Establish meaning and scope

Identify the question the diagram answers and its audience. Read the relevant
repository, configuration, or documents when a factual diagram is requested.
Keep a brief source record. Mark unsupported claims as `inferred` or `proposed`;
do not label them `observed`. An illustrative example must say it is
illustrative.

Prefer one readable primary story. Separate context, detail, and alternate
concerns with named views or separate artifacts. Do not confuse logical
containment, deployment, team ownership, and chronology. Each node can have
only one containment parent; other dimensions belong in metadata, tags,
relationships, and views.

### 2. Author the source JSON

Start from the closest model in `examples/`. Follow
`assets/diagram.schema.json` and the semantic validator. Use stable IDs,
explicit leaf endpoints, and short labels. Put explanations, links, ownership,
and evidence in metadata or descriptions.

Use the optional validated `appearance` object for supported leaf shapes, colors,
stroke widths and group-label placement. Do not add `x/y`, raw CSS, HTML labels,
SVG fragments, URL icons, ports, or edge routing flags to the model. Unknown
fields fail validation rather than being silently ignored. An empty boundary is
an ordinary node, not an empty compound group. A group has `kind: "group"`; its
members use `parent`. Group shapes and non-group `groupLabel` values are
rejected by the validator.

### 3. Resolve icons

Reuse a meaningful bundled icon or omit `icon`. Run
`python3 scripts/diagram.py icons` for the registry. Bundled identifiers are
namespaced by source where needed, such as `tabler-*`, `lucide-*`, `mdi-*`, and
`simple-*`. For a new icon, vendor only the needed SVG, record its
source/version/license/attribution, and import it through the allowlist script.
Never install an entire icon ecosystem merely to draw a few symbols. See
[icons.md](references/icons.md).

### 4. Validate, build, and browser-check

Run commands from the Topoform directory, or resolve scripts relative to this
file; do not assume the user's working directory is the skill directory.

```bash
python3 scripts/diagram.py doctor
python3 scripts/diagram.py validate /path/to/diagram.json
python3 scripts/deliver.py /path/to/diagram.json /path/to/diagram.html \
  --evidence /path/to/diagram-checks
```

`deliver.py` builds a candidate and replaces the output only after browser
checks pass. It does not certify visual quality. Its receipt keeps visual
review pending. Build or browser failure leaves a previous output intact; a
receipt failure after promotion reports that the new artifact was delivered.

For a build-only environment:

```bash
python3 scripts/diagram.py build /path/to/diagram.json /path/to/diagram.html
```

Report browser execution and visual review as **not run**; never invent
screenshots or claim runtime verification from a syntax check.

If direct `file://` or loopback navigation is unavailable, `--load content`
executes the exact compiled HTML bytes in an offline browser context. Use it
only when appropriate and disclose that direct file navigation was not
verified.

### 5. Inspect the actual screenshots

Open the desktop, wide, and mobile images and the exported PNG with an
image-viewing tool. Check labels, arrows, icons, hierarchy boundaries,
crossing ambiguity, text contrast, and container clipping. An absence of
JavaScript errors is not visual approval.

Below-10px overview text is a warning, not success. A long flow can be
structurally correct but illegible when fitted into one viewport. Prefer a
focused view, a separate detail diagram, or the text representation. Do not
silently remove relationships to improve appearance.

Repair errors in the model first. Change supported direction and spacing
settings only when they improve the message. Keep two bounded repair rounds;
then disclose any remaining limitation and preserve the source rather than
patching arbitrary coordinates or pretending the renderer supports precision
routing.

### 6. Deliver and preserve

Provide the HTML and JSON source plus the verification receipt. State the
tested browser/version, network mode, warnings, and untested surfaces. State
exactly which screenshots were inspected. Preserve third-party notices and
icon credits in both the skill and generated artifact.

When revising a diagram, edit JSON and rebuild. Do not export `cy.json()` as
source: it contains runtime presentation state. Search, focus, and filter
changes must not rewrite source topology. PNG-all must not inherit temporary
hidden or dimmed state.

## Included behavior

Automatic layered node placement; directed and undirected edges; compound
nested groups; validated node shapes and colors; top or inside group labels
with optional group icons; pan/zoom/fit; four flow directions; named views with ancestor
context; edge-kind filtering; keyboard-accessible search;
neighbour/upstream/downstream inspection; metadata and safe links; all-model
text tables; source JSON download; PNG of the current view or full model; and
offline local SVG icons with credits.

## Important boundaries

The stack is **Cytoscape.js → cytoscape-elk → ELK.js → Cytoscape
positions/rendering**. The adapter is essential. Load libraries before the
viewer. Use `name: 'elk'` and `elk.algorithm: 'layered'`.

The adapter applies node positions, not ELK edge sections, ports, or label
placement. After layout, this viewer derives distinct Cytoscape surface
endpoints and collision-aware label offsets as presentation state; it still
uses Cytoscape's own bezier edges.
`elk.edgeRouting: 'ORTHOGONAL'` would not make those edges ELK-routed. Core
Cytoscape is Canvas, not a native SVG export engine.

The bundled adapter creates ELK without a real external Web Worker. The
viewer's 15-second timeout is a failure signal, not hard cancellation or
protection against a blocked main thread. `stop()` in this adapter does not
cancel computation. See the composition guidance before adding worker support.

Do not advertise built-in collapse/expand, graphical editing, live cloud
discovery, authenticated dashboards, SVG export, or live impact analysis.
These need distinct implementations and tests. General-purpose graphs do not
mean every specialist diagram grammar.

## Regression checks after changes

```bash
python3 -m unittest discover -s tests -p test_model.py -v
python3 tests/run_browser.py --out /path/to/regression-evidence
```

Browser tests need Playwright and Chromium; use an approved installation or
install the test dependencies explicitly. Re-run the matrix after dependency,
styling, schema, icon, or renderer changes. Do not silently update dependency
versions. See README and the vendor manifest for the tested baseline and its
provenance.
