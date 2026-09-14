# Icons: source, meaning, packaging and safety

## Choose meaning before branding

An icon should clarify the element's role, not make the drawing look cloud-specific. A person, document, queue, store, process or physical device usually deserves a generic symbol. Use a brand logo only when the model explicitly identifies that product. Never replace “database” with a PostgreSQL logo merely because one is available.

Prefer one generic icon family per diagram; mix in a few necessary brand marks rather than mixing several inconsistent stroke/filled families. Icons are secondary to labels. Keep text and symbols legible without relying only on color. Preserve source proportions, especially for brand marks.

## Available sources

Topoform ships 114 reviewed icons from five packs. The registry keeps generic
and brand identifiers distinct with source namespaces where needed:

| Pack | Version | Count | Good for | License handling |
|---|---:|---:|---|---|
| Font Awesome Free Solid | 6.7.2 | 21 | People, documents, stores, devices, tasks | CC-BY-4.0; attribution and modifications are recorded |
| Tabler Icons | 3.35.0 | 24 | Broad generic outline vocabulary | MIT; preserve `TABLER.LICENSE.txt` |
| Lucide | 0.544.0 | 24 | Consistent generic outline vocabulary | ISC, with Feather-derived MIT portions |
| Material Design Icons | 7.4.47 | 24 | Generic and product-adjacent concepts | Apache-2.0; preserve `MDI.LICENSE.txt` |
| Simple Icons | 15.15.0 | 21 | Explicitly named software/tool brands | Per-icon terms and trademark guidance; read the disclaimer |

Identifiers from the namespaced packs use prefixes such as `tabler-*`,
`lucide-*`, `mdi-*`, and `simple-*`. The original Font Awesome generic IDs are
retained where they are unambiguous. Official AWS Architecture Icons are not
bundled.

Useful primary sources: [Lucide static assets](https://lucide.dev/guide/static/),
[Lucide license](https://lucide.dev/license), [Tabler repository](https://github.com/tabler/tabler-icons),
[Material Design Icons](https://github.com/Templarian/MaterialDesign),
[Iconify icon data](https://iconify.design/docs/icons/icon-data.html),
[Iconify utilities](https://iconify.design/docs/libraries/utils/),
[Simple Icons disclaimer](https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md),
and [Font Awesome Free license](https://fontawesome.com/license/free).

The reference artifact bundles **SVG paths, not fonts**. Do not include icon fonts or system font files in a handoff. Font Awesome's code, icons and font files have different licenses; the icon-specific CC-BY terms apply to this SVG subset.

## Registry and directory layout

```text
assets/icons/
  manifest.json
  LICENSE.txt
  TABLER.LICENSE.txt
  LUCIDE.LICENSE.txt
  MDI.LICENSE.txt
  SIMPLE_ICONS.LICENSE.md
  SIMPLE_ICONS.DISCLAIMER.md
  person.svg
  tabler-*.svg
  lucide-*.svg
  mdi-*.svg
  simple-*.svg
```

A node contains `"icon": "person"`, not inline SVG or a remote URL. The registry decouples semantic model identifiers from physical icon files:

```json
{
  "person": {
    "path": "person.svg",
    "pack": "Font Awesome Free Solid",
    "version": "6.7.2",
    "source": "https://github.com/FortAwesome/Font-Awesome/blob/6.7.2/svgs/solid/user.svg",
    "license": "CC-BY-4.0",
    "attribution": "Fonticons, Inc.",
    "modifications": "Explicit dimensions; normalized static fill.",
    "sha256": "<SHA-256 of the actual local SVG bytes>"
  }
}
```

The builder verifies file containment and hash, sanitizes the SVG, embeds only the icons the model uses, and carries source/license/attribution into the HTML credits. Its PNG footer also attaches attribution; retain the HTML/manifest for full provenance when redistributing raster exports. A license notice in this package does not grant rights to some other logo you add later.

## Import workflow

Obtain a reviewed SVG from a primary distribution or official repository. Resolve Iconify aliases, flips/rotations and dimensions using `getIconData`/`iconToSVG` from its documented utilities rather than naïvely copying a `body` field. Expand symbol/use references to static paths when needed. Save the result locally; preserve its original source and license separately.

```bash
python3 scripts/import_icon.py reviewed-icon.svg \
  --id sample-symbol \
  --source https://example.org/exact-version/icon.svg \
  --license MIT --attribution "Actual rights holder" \
  --pack "Actual pack" --version "Exact version" \
  --icons project-icons
```

The URL above is a placeholder for your actual provenance URL, not an icon download service. The importer does not fetch URLs or infer licenses. It refuses to overwrite an existing ID. Keep a copy of the relevant upstream license in the registry directory. To combine your new icons with the built-ins, first copy the bundled registry into a project-owned directory, then import there; build with `--icons project-icons`.

## Browser composition

Cytoscape supports data-URI background images. The builder URI-encodes a static SVG with explicit namespace, viewBox, width and height. It resolves `currentColor` because an image does not inherit the node's CSS text color. It uses a trusted fixed XML header, not a user-supplied DTD.

The viewer uses a small explicit background width/height and `background-fit: none`. Combining `contain` with small numeric dimensions made the bundled icons fill the card in actual testing. The fixed dimensions are now regression-tested and screenshots inspected. Image decode completes before the graph is laid out/exported.

Remote icon loading is disabled. It would undermine offline use, leak viewer requests and potentially taint Canvas exports through CORS. Prefer build-time vendoring over runtime calls to Iconify/CDNs. The document CSP permits only data/blob images, not remote image hosts.

## Safe static subset, not a universal sanitizer

The importer/build rejects scripts, foreignObject, image, use, event handlers, hrefs, resource URLs, style tags/attributes, CSS variables, entities and arbitrary DTDs. Accepted elements are SVG/g/path plus simple geometry and title/description. viewBox dimensions must be finite and positive. Files over 100 KB fail.

This intentionally rejects some legitimate complex SVGs. Do not weaken the allowlist just to make an unknown asset load. Obtain a flattened trusted path-only version or choose a simpler icon. The allowlist reduces active-content risk; it is not a formal security certification or a license checker. Do not rasterize an untrusted SVG in a privileged service as an automatic workaround.

## Visual check

Look for distortion, tiny strokes, clipped paths, missing icons, inappropriate logos, icon/label overlap and exported image failures. A correct hash proves integrity relative to the registry, not that the icon is accurate, safe in every environment or legally suitable for every purpose.
