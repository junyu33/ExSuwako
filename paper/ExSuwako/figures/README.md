# Manuscript figure renderings

These PDFs are presentation copies of hash-locked SVGs rebuilt by
`make artifact-paper`.  The CSV inputs and complete generated artifact remain
outside Git under `bench/data/`; only figures actually included by
`paper/ExSuwako/main.tex` are retained here so that the manuscript compiles in
the remote editor.

| PDF | Canonical SVG | SVG SHA-256 |
|---|---|---|
| `winner-panels.pdf` | `winner-panels.svg` | `e5426e0c49dcad6435981e548aebf46e763dfeb9308db5cb939b2df737becc3b` |
| `work-runtime.pdf` | `work-runtime.svg` | `2155f65234a2806d2c1d0e02ad45c0b914c7312fcd8d6fe970d08efc9f58d808` |
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
