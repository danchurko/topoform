# Third-party notices

Original Topoform code and documentation are MIT-licensed. The distribution is
not uniformly MIT: bundled runtime libraries and icons retain their own
licenses. Keep the license files under `assets/vendor/` and `assets/icons/`
with any redistribution.

## Browser runtime

The generated artifact embeds these exact official npm package distributions.
`assets/vendor/manifest.json` records the package version, source, license
file, and SHA-256 digest for every distributed runtime file.

### Cytoscape.js 3.33.1

MIT. Source: [npm package](https://www.npmjs.com/package/cytoscape/v/3.33.1)
and [upstream repository](https://github.com/cytoscape/cytoscape.js/tree/v3.33.1).
License: `assets/vendor/cytoscape.LICENSE.txt`.

### ELK.js 0.9.3

Eclipse Public License 2.0. Source: [npm package](https://www.npmjs.com/package/elkjs/v/0.9.3)
and [upstream repository](https://github.com/kieler/elkjs/tree/0.9.3).
License: `assets/vendor/elkjs.LICENSE.txt`.

### cytoscape-elk 2.3.0

MIT. Source: [npm package](https://www.npmjs.com/package/cytoscape-elk/v/2.3.0)
and [upstream repository](https://github.com/cytoscape/cytoscape.js-elk/tree/v2.3.0).
License: `assets/vendor/cytoscape-elk.LICENSE.txt`.

The viewer uses Cytoscape.js for graph interaction and Canvas rendering, ELK.js
for layered layout, and cytoscape-elk as the adapter. The adapter applies node
positions; it does not turn this viewer into an ELK port or edge-section
renderer.

## Bundled icon packs

The catalogue contains 114 selected static SVGs. Every registry entry records
the upstream source, exact version, license, attribution, modifications, and
SHA-256 digest in `assets/icons/manifest.json`.

### Font Awesome Free Solid 6.7.2 — 21 icons

SVG icons are licensed CC-BY-4.0 by Fonticons, Inc. Sources are the
[6.7.2 Solid assets](https://github.com/FortAwesome/Font-Awesome/tree/6.7.2/svgs/solid)
and [Font Awesome's free license](https://fontawesome.com/license/free).
The full notice is in `assets/icons/LICENSE.txt`; the package notice is in
`assets/vendor/fontawesome.LICENSE.txt`. No Font Awesome font files are
distributed.

### Tabler Icons 3.35.0 — 24 icons

MIT. Sources are the [v3.35.0 icon assets](https://github.com/tabler/tabler-icons/tree/v3.35.0/icons/outline)
and [Tabler repository](https://github.com/tabler/tabler-icons). License:
`assets/icons/TABLER.LICENSE.txt`.

### Lucide 0.544.0 — 24 icons

ISC for Lucide, with MIT-licensed portions derived from Feather Icons. Sources
are the [v0.544.0 icon assets](https://github.com/lucide-icons/lucide/tree/0.544.0/icons)
and [Lucide license](https://lucide.dev/license). License:
`assets/icons/LUCIDE.LICENSE.txt`.

### Material Design Icons 7.4.47 — 24 icons

Apache License 2.0 for the redistributed icons. Source: [v7.4.47 SVG
assets](https://github.com/Templarian/MaterialDesign/tree/v7.4.47/svg).
License: `assets/icons/MDI.LICENSE.txt`.

### Simple Icons 15.15.0 — 21 icons

The Simple Icons collection is CC0, but individual brand icons can have
different copyright, license, or trademark requirements. Source:
[v15.15.0 icons](https://github.com/simple-icons/simple-icons/tree/15.15.0/icons).
Read both `assets/icons/SIMPLE_ICONS.LICENSE.md` and
`assets/icons/SIMPLE_ICONS.DISCLAIMER.md`, and check the upstream guidance for
each brand before redistributing an exported image.

Brand marks identify the named product or company; their inclusion does not
imply endorsement, affiliation, or permission to use a trademark outside its
owner's guidance. Official AWS Architecture Icons are not bundled.

## Notices in generated artifacts

Topoform embeds credits for the icons used by a model in the generated HTML
and PNG footer. Retain the source model, artifact credits, registry, and these
notices together when distributing an artifact. A package license does not
grant rights to an icon or logo that is added outside the reviewed catalogue.
