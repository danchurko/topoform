# Quality gates and known limits

## Independent gates

**Model gate:** correct schema; existing and unique IDs; valid endpoints; single-parent acyclic hierarchy; defined icons; safe asset paths; acceptable links; evidence status; no silent unsupported fields. Passing proves the model is internally consistent, not that it matches reality.

**Browser gate:** execute the actual compiled file; wait for asynchronous readiness; verify finite node and edge geometry, parent containment, non-overlapping leaf bodies, visible edge counts, image dimensions, PNG decode, source immutability and no unexpected network requests. Save desktop/wide/mobile screenshots and exact artifact hash. A script's syntax check is not this gate.

**Perceptual gate:** open the screenshot and exported PNG. Inspect font size, label clipping, crossing ambiguity, icons and hierarchy. The automated audit checks the tested label bounds and routed endpoints, but does not perform OCR, understand every crossing, or provide full accessibility testing. It must never claim visual quality merely because geometric assertions pass.

`deliver.py` gates replacement on the first two, leaving the third explicitly pending. An agent should inspect the saved images before presenting the result as visually reviewed. Preserve the reviewed artifact's SHA-256 in any review note.

## Reference behavior vs aspirations

| Issue | Baseline behavior | Required response |
|---|---|---|
| Empty model | Clear empty state, no crash | No PNG to export |
| Disconnected nodes | ELK positions them | Inspect grouping/ordering for meaning |
| Cycles, self-loops, opposite/parallel edges | Rendered, semantic direction retained | Inspect label/route readability |
| Nested/cross-boundary edges | `INCLUDE_CHILDREN`; translated ancestor offsets | Use real leaf endpoints; verify containment |
| Node/edge labels | Wrapped; leaves measured first | Shorten only without losing meaning; move detail to inspector |
| Long linear graph | Can fit to very small text | Use a focused/detail view; do not certify unreadable overview |
| Dense graphs | Warning above 45 nodes | Split artifacts for layout performance; views alone do not reduce input |
| Mobile | Controls stack; canvas pans/zooms; inspector below | Use focused views or Text view for reading |
| Canvas accessibility | Native controls, keyboard search and text table alternative | Not full keyboard traversal or a certified screen-reader graph |
| ELK job rejects | Visible fail-closed status; disabled controls | Repair model/integration and reload |
| ELK computation stalls | 15-second soft deadline | Not true cancellation; use worker-based integration for hard isolation |
| Routes/labels collide | Tested node/label bounds and endpoints are machine-checked; arbitrary crossings remain a visual concern | Visual review; split view or use a suitable route-aware renderer |
| Time-scaled sequence/swimlane/BPMN | No specialist semantics | Use another appropriate diagram grammar |

## Regression coverage

The tests and screenshots cover concrete failure modes:

1. Raw ES-class adapter registration conflicted with Cytoscape's function-style invocation. The source-composed adapter now uses the upstream distribution's constructor shape.
2. An `undefined` final filter condition toggled every edge into the hidden class. The condition is now explicitly boolean and initial edge counts are asserted.
3. `background-fit: contain` oversized fixed-size SVG icons. The baseline uses `none` with explicit small dimensions, followed by actual image decode and screenshot inspection.
4. A shared highlight width risked changing node size. Node and edge highlight selectors are separate, with width-stability tests.
5. Immediate visibility queries could observe lazy cached styles after filtering. Display styles are resolved before status/traversal queries; ancestor-only views and hidden-node search are regression-tested.
6. Root-only spacing did not uniformly set compound-subgraph gaps. The baseline passes applicable spacing/padding into `nodeLayoutOptions`.
7. Edge labels can exceed the interlayer gap because ELK never receives them from this adapter. The viewer wraps them to a bounded gap width; visual review is still required.

8. A self-loop counted as visible but had a NaN endpoint and was not drawn. A dedicated loop style with sufficient control-point distance corrected it; the browser audit now checks edge endpoints, midpoints and control points, not only node coordinates.

These checks do not imply every conceivable graph has a readable layout. The
regression suite includes nested flows, cycle/self-loop examples, and a
dense-graph benchmark so validation exercises failure boundaries as well as
successful models.

## Determinism

Same model and bundled assets produce byte-identical HTML. Repeated layout of the tested reference model preserved positions within the suite's tolerance. This is not a universal cross-browser/OS/font/version layout guarantee. Changing topology, source order, font metrics or ELK versions can move nodes. Avoid falsely presenting layout movement as an architecture change.

## Security and deployment

Model labels are text, not HTML. JSON is escaped against closing-script injection. Icons use a strict static subset. Links and asset paths are checked. The self-contained page has a restrictive CSP and no runtime fetches. Inline scripts/styles are deliberately allowed because it is one trusted generated file; this is not a general untrusted-HTML hosting sandbox.

The viewer carries everything in the JSON into the HTML, including hidden views and metadata. **Filtering is not access control.** Do not embed secrets or sensitive details in a shareable artifact. The tool does not scan your repository for secrets.

HTML preview environments may strip scripts or block Canvas. Download/open the
artifact in an approved browser or provide the PNG as a fallback. If a browser
policy requires exact HTML-content loading instead of direct `file://` or
loopback navigation, record that limitation. No Safari/Firefox/real touch
device or deployment-embedding certification is claimed.

## Extension criteria

Add only a capability with a real requirement and observable tests. For collapse/expand, keep the original model immutable and define what projected aggregate edges mean; a hidden group must not silently drop external connectivity. For live status, distinguish observation timestamps and stale data from authored topology. For SVG export, use a compatible export extension or another renderer and test icons/fonts/clipping independently. For very large graphs, profile real data before moving to workers or a different renderer.

An adversarial nested-cycle case can still route a return edge behind an
unrelated node. It is not an approved presentation view. Passing the
structural suite must not erase this visual limitation.
