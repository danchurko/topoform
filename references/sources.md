# Primary sources and verification scope

Researched on 2026-09-14. Dynamic documentation may change; exact tested versions and local hashes live in `assets/vendor/manifest.json`. Upstream feature availability is not proof this adapter/viewer exposes it.

| Source | Used for |
|---|---|
| [Cytoscape documentation](https://js.cytoscape.org/) | Elements, parent model, styles, image backgrounds, interaction, traversal, layout API, Canvas and PNG export |
| [cytoscape-elk README](https://github.com/cytoscape/cytoscape.js-elk) | Browser/module composition and layout options |
| [Adapter v2.3.0 layout source](https://github.com/cytoscape/cytoscape.js-elk/blob/v2.3.0/src/layout.js) | Actual field transfer, ancestor offsets, leaf-position application, no port/route/label forwarding, no-op cancellation |
| [Adapter v2.3.0 distribution](https://github.com/cytoscape/cytoscape.js-elk/blob/v2.3.0/dist/cytoscape-elk.js) | Function/prototype constructor compatibility with extension registration |
| [ELK.js 0.9.3 README](https://github.com/kieler/elkjs/blob/0.9.3/README.md) | Bundled browser build, explicit worker integration, Promise API, available-option discovery, worker termination |
| [ELK layered reference](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html) | Layered layout, hierarchy and ports/routing capabilities of ELK itself |
| [Lucide static guide](https://lucide.dev/guide/static/) and [license](https://lucide.dev/license) | Optional generic SVG source and license checking |
| [Iconify data](https://iconify.design/docs/icons/icon-data.html) and [utilities](https://iconify.design/docs/libraries/utils/) | Build-time icon collections, alias/transform handling and avoiding unnecessary runtime API calls |
| [Font Awesome Free license](https://fontawesome.com/license/free) and [6.7.2 assets](https://github.com/FortAwesome/Font-Awesome/tree/6.7.2/svgs/solid) | Actual bundled generic SVG source, version and icon license |
| [Tabler Icons](https://github.com/tabler/tabler-icons/tree/v3.35.0/icons/outline) | Bundled generic SVG source, version, and MIT license |
| [Material Design Icons](https://github.com/Templarian/MaterialDesign/tree/v7.4.47/svg) | Bundled SVG source, version, and Apache-2.0 license |
| [Simple Icons disclaimer](https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md) | Brand/trademark rights are distinct from file licensing |
| [MDN Canvas and cross-origin images](https://developer.mozilla.org/en-US/docs/Web/HTML/How_to/CORS_enabled_image) | Remote-image/CORS export risk |
| [Agent Skills specification](https://agentskills.io/specification) | Portable SKILL.md frontmatter and progressive resource directories |

The runtime refresh path stages exact package versions from npm before explicit
review. The active runtime manifest records package origins, licenses, and
SHA-256 digests; browser and visual checks remain required after a refresh.
