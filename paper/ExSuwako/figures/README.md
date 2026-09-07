# Manuscript figure renderings

These PDFs are presentation copies of hash-locked SVGs rebuilt by
`make artifact-paper`.  The CSV inputs and complete generated artifact remain
outside Git under `bench/data/`; only figures actually included by
`paper/ExSuwako/main.tex` are retained here so that the manuscript compiles in
the remote editor.

| PDF | Canonical SVG | SVG SHA-256 |
|---|---|---|
| `winner-panels.pdf` | `winner-panels.svg` | `47e0596ecde337bc2492742e787f4f3f869ee53f90efa9cf4fcd8262b785fc2d` |
| `work-runtime.pdf` | `work-runtime.svg` | `d3bb2e45ce658d1359285f4a039176e34bca67fa8d4098462cb962f1b79c0bbc` |

The checked-in PDFs were rendered with `rsvg-convert` 2.62.3:

```text
rsvg-convert -f pdf winner-panels.svg -o winner-panels.pdf
rsvg-convert -f pdf work-runtime.svg -o work-runtime.pdf
```
