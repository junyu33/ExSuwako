# Manuscript figure renderings

These PDFs are presentation copies of hash-locked SVGs rebuilt by
`make artifact-paper`.  The CSV inputs and complete generated artifact remain
outside Git under `bench/data/`; only figures actually included by
`paper/ExSuwako/main.tex` are retained here so that the manuscript compiles in
the remote editor.

| PDF | Canonical SVG | SVG SHA-256 |
|---|---|---|
| `winner-panels.pdf` | `winner-panels.svg` | `9187e9c114a51fcc50380a8072700e680929522b0b55716e669a6af8ea7f74a8` |
| `work-runtime.pdf` | `work-runtime.svg` | `c73c091a8af139710483d060c6b16bd8a2802dd602f36484c3f53bedc2c717b6` |
| `rabin-e2e.pdf` | `rabin-e2e.svg` | `970efee290a22fd84869f2aa0ebc95e6700ada3f692ae1489c664d3963bcaa2f` |

The checked-in PDFs were rendered with `rsvg-convert` 2.62.3 and normalized
to PDF 1.5 for compatibility with the journal class:

```text
rsvg-convert -f pdf winner-panels.svg -o winner-panels.pdf
rsvg-convert -f pdf work-runtime.svg -o work-runtime.pdf
rsvg-convert -f pdf rabin-e2e.svg -o rabin-e2e.pdf
gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 \
  -sOutputFile=winner-panels-v1.5.pdf winner-panels.pdf
gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 \
  -sOutputFile=work-runtime-v1.5.pdf work-runtime.pdf
gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 \
  -sOutputFile=rabin-e2e-v1.5.pdf rabin-e2e.pdf
```
