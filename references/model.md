# Topoform diagram model contract

The source is ordinary UTF-8 JSON, validated by `scripts/diagram.py`. Duplicate JSON keys and nonfinite numbers fail during parsing. The structural JSON Schema helps editors; semantic validation additionally checks identity, containment, endpoints and evidence.

## Minimal model

```json
{
  "schemaVersion": 1,
  "title": "Editorial review",
  "description": "A proposed workflow, not observed production behavior.",
  "nodes": [
    {"id": "author", "label": "Author", "kind": "person", "icon": "person"},
    {"id": "review", "label": "Review team", "kind": "group"},
    {"id": "editor", "label": "Editor", "kind": "person", "parent": "review"},
    {"id": "article", "label": "Published article", "kind": "artifact", "icon": "document"}
  ],
  "edges": [
    {"id": "submit", "source": "author", "target": "editor", "label": "Draft", "kind": "handoff"},
    {"id": "publish", "source": "editor", "target": "article", "label": "Approve", "kind": "handoff"}
  ]
}
```

## Fields

Top level: required `schemaVersion: 1`, `title`, `nodes`, `edges`. Optional `description`, `views`, `layout`, `metadata`. Unknown topological/presentation fields fail rather than being ignored. Extend domain detail inside `metadata`.

A node requires `id`, `label`. Optional `kind` (any nonempty meaningful string), `parent`, `icon`, `description`, `tags`, `metadata`, `links`, `evidence`. `group` is the only special kind. Ordinary nodes can represent people, states, components, machines, documents, teams, processes, stores or concepts.

An edge requires `id`, `source`, `target`. Optional `label`, `kind`, `directed` (default true), `description`, `tags`, `metadata`, `links`, `evidence`. Node and edge IDs share one namespace. Repeated endpoint pairs are permitted with different edge IDs. Self-loops produce a warning; cycles are permitted. A two-headed relationship should be modeled deliberately: one undirected association or two distinct directed relations, not a decorative second arrow.

IDs start with a letter, use letters/digits/underscore/dot/colon/hyphen and are at most 96 characters. `root` and JavaScript prototype-like names are reserved because the adapter uses plain lookup objects. Labels are not IDs. Source order is preserved; use stable ordering across revisions to reduce unnecessary layout churn. Exact positions are not stable across arbitrary graph edits or dependency versions.

`links` is an array of `{ "label": "Documentation", "url": "https://…" }`. Only explicit HTTP(S) URLs without credentials/control characters are allowed. The UI inserts text with `textContent` and opens links with `noopener noreferrer`.

`evidence` is `{ "status": "observed|declared|inferred|proposed", "source": "…" }`. An observed claim must include a source. This is an authoring discipline, not automated proof that the source is correct. Use a commit/path/line reference or document section where practical. Do not turn a design hypothesis into a deployment claim.

## Containment

`parent` is one existing group ID. The parent graph is acyclic. Empty groups fail: Cytoscape would treat them as ordinary nodes, not compounds. Maximum supported depth is 12; this is a defensive ceiling, not a recommendation to draw twelve nested boxes.

Relationships target concrete leaf elements. Connect to a named interface/member when a relationship conceptually crosses a subsystem boundary. Do not add a fake interface merely to satisfy rendering: identify a real one or represent the subsystem as a leaf in a separate high-level model. Group endpoints and parent-to-descendant edges are rejected by this baseline.

A group's visual box means the containment you authored. It does not automatically mean trust, network reachability, resource ownership or authorization. Put that meaning in its label/description. A node cannot be both inside a team and inside a region as two parents. Choose one hierarchy; use tags, views and metadata for the other dimension.

## Views

```json
{"id":"delivery","label":"Delivery path","nodeIds":["editor","article"],"edgeKinds":["handoff"]}
```

A view selects existing nodes. Selecting a group explicitly includes its descendants. Selecting a leaf adds ancestors for context, but does **not** add unrelated siblings merely because their parent is visible. Only source edges with both endpoints visible remain, optionally restricted by `edgeKinds`. Global edge-kind filtering is an additional intersection. Views do not invent summary/aggregate edges.

`all` is reserved for the full model. An empty view is valid and shows an empty-state message; its PNG export has nothing to export. No elements are deleted. Switching views preserves source-model coordinates; hidden-member removal can resize compound boxes.

## Layout

`layout` accepts `direction` (`RIGHT`, `DOWN`, `LEFT`, `UP`), `spacing` (30–1000), and `layerSpacing` (60–1000). The baseline algorithm is layered. Coordinates, ports, raw layout-engine options and per-group direction overrides are not in this schema. Change the integration deliberately when that is genuinely required.

Leaf text is wrapped/measured before layout. Icons occupy a fixed small region of the card. Keep node labels concise and edge labels even shorter; this adapter does not reserve ELK space for edge labels. The viewer limits edge label wrapping width to the available interlayer gap, but this cannot guarantee every label avoids every route.

The validator warns above 45 nodes and caps input at 1000 nodes/4000 edges. The cap is not a performance or readability guarantee. Named views help readers but the baseline still lays out the whole model; split very large sources into separate artifacts or build a worker-based application after measurement.
