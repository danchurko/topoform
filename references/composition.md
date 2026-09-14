# Composition and extension points

## The correct stack

Cytoscape owns the graph, styling, Canvas rendering, interaction and exports. ELK calculates layout geometry. `cytoscape-elk` adapts Cytoscape elements to ELK and applies returned node positions. They are not interchangeable libraries.

For official browser distribution files, the order is:

```html
<script src="cytoscape.min.js"></script>
<script src="elk.bundled.js"></script>
<script src="cytoscape-elk.js"></script>
<script src="viewer.js"></script>
```

The browser extension auto-registers when globals exist. In a bundled module application, follow the adapter README's import style and call `cytoscape.use(elkExtension)` once. Do not combine accidental global and module instances of Cytoscape. This skill compiles the equivalent load order into one HTML file.

```js
cy.layout({
  name: 'elk',
  fit: false,
  animate: false,
  nodeDimensionsIncludeLabels: false,
  elk: {
    'elk.algorithm': 'layered',
    'elk.direction': 'RIGHT',
    'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
    'elk.spacing.nodeNode': 65,
    'elk.layered.spacing.nodeNodeBetweenLayers': 120
  },
  stop: () => { /* inspect finite coordinates, apply filters, then fit */ }
}).run();
```

Here labels are measured inside explicit leaf-card dimensions before layout, so including external label dimensions again would double-count them. The skill passes spacing/padding to compound subgraphs using `nodeLayoutOptions`, rather than assuming every root option is inherited. Separate per-group flow directions are not exposed: a quick mixed-direction experiment did not reliably override the integrated cross-hierarchy layout.

## What actually crosses the adapter boundary

This is based on the v2.3.0 implementation, not the combined feature lists of both products.

| Capability | Underlying support | Reference viewer |
|---|---|---|
| Layered leaf-node positions | ELK, applied by adapter | Included |
| Compound hierarchy | ELK children + Cytoscape parents | Included; leaf endpoints only |
| Cross-hierarchy edges | Layered with `INCLUDE_CHILDREN` | Tested |
| Cycles, parallel edges, self-loops | Graph + layout + renderer | Tested; inspect routing visually |
| Alternative ELK algorithms | ELK's available algorithms | Documented, not exposed/tested in UI |
| ELK ports and port constraints | Direct ELK JSON supports them | Adapter does not forward node ports; viewer derives surface endpoints |
| ELK orthogonal edge sections | ELK can calculate them | Adapter does not apply them to Cytoscape |
| ELK edge-label placement | Direct ELK label geometry | Adapter does not forward labels; viewer offsets labels after layout |
| PNG/JPEG | Cytoscape core exports | PNG with title/credits included |
| SVG | Additional export integration | Not included |
| Collapse/expand, minimap | Extensions or custom projection | Not included |
| User editing and persistence | Custom application layer | Not included |

`makeEdge()` copies IDs and endpoints, not labels or port attachments. `applyLayout()` applies leaf positions and ancestor offsets, not returned edge sections. After layout, the viewer assigns geometry-derived Cytoscape surface endpoints, separates parallel/reverse lanes, and chooses label offsets that avoid the tested node and label bounds. Do not advertise `elk.edgeRouting = ORTHOGONAL` as a way to reroute this viewer's lines. They remain Cytoscape bezier edges. Taxi/segment styles would still be Cytoscape routes, not ELK obstacle-aware routes.

If exact routes are a hard requirement, either build and test a direct-ELK geometry adapter that maps node centers, nested offsets, ports and every edge section into a compatible renderer, or choose a renderer built for that geometry. Do not sneak this large change into a styling patch. Keep source IDs/topology stable.

## Lifecycle and race handling

Wait for the container to have nonzero dimensions, document fonts, and icon decode before measuring/layout. Cytoscape should not run its normal initial layout; use `preset`, then explicitly request ELK. Parent bounds are recomputed by Cytoscape from children; do not assume they exactly reproduce ELK's parent dimensions.

ELK is asynchronous. Use one in-flight layout and wait for completion before fit/export. This adapter's `stop()` and `destroy()` are no-ops; calling them does not cancel an ELK job. The bundled viewer locks controls, checks completion, handles unhandled layout rejection visibly and times out after 15 seconds. A synchronous main-thread stall can delay even that timer; it is not a hard execution quota.

Changing a named view or edge filter hides elements without re-running layout. Before an explicit relayout, restore every source element so hidden-node dimensions do not distort ELK's input; reapply filters afterward. Flush lazy Cytoscape display styles before same-turn visibility queries. Always pass a real boolean to `toggleClass`; `undefined` toggles instead of explicitly clearing a class.

## Workers: optional, not an implied property of a Promise

`new ELK()` from the bundled distribution works without an external Web Worker. The adapter instantiates it this way. This skill has `worker-src 'none'` and makes no off-main-thread claim.

The documented direct-ELK worker setup uses `elk-api.js` plus a `workerUrl` for `elk-worker.js`/`elk-worker.min.js`. That requires an explicit integration, worker lifecycle management, suitable HTTP serving and CSP, and tests for worker failure. A true single-file Blob worker is another integration with its own CSP/packaging tradeoffs; it is not provided here. For repeated layouts in a larger app, reuse the worker and use request IDs to reject stale results. `terminateWorker()` is a direct-ELK method, not something this stock adapter exposes as real cancellation.

## Source and version discipline

Check `assets/vendor/manifest.json`, not a CDN's moving `latest` URL. Build
verifies hashes and preserves licenses. The bundled browser files come from
the exact official npm distributions of Cytoscape.js 3.33.1, ELK.js 0.9.3,
and cytoscape-elk 2.3.0; the manifest records package sources, versions,
licenses, and SHA-256 digests.

To stage official npm browser files in a connected environment, without altering the installed skill implicitly:

```bash
npm install --prefix diagram-deps --save-exact \
  cytoscape@3.33.1 elkjs@0.9.3 cytoscape-elk@2.3.0
python3 scripts/vendor_from_npm.py diagram-deps/node_modules \
  --out diagram-vendor-candidate
```

Review staged versions and licenses, back up `assets/vendor`, replace it
explicitly, and rerun unit tests, the browser matrix, and screenshot review. A
newer version is a separate upgrade decision. Record new hashes and browser
evidence. Staging is not a security audit.

Use the official transpiled adapter distribution. Cytoscape invokes extensions
with `.apply()`, so the published function/prototype constructor shape is part
of the compatibility boundary. Do not change the adapter constructor without
rerunning a browser test.

Primary sources: [adapter README](https://github.com/cytoscape/cytoscape.js-elk), [tagged layout implementation](https://github.com/cytoscape/cytoscape.js-elk/blob/v2.3.0/src/layout.js), [ELK 0.9.3 README](https://github.com/kieler/elkjs/blob/0.9.3/README.md), [Cytoscape API](https://js.cytoscape.org/).
