# Layout-proxy style file: NOT the official NeurIPS 2026 style

* File: `neurips_2026_COMMUNITY_COPY_NOT_OFFICIAL.sty`
* Source: https://raw.githubusercontent.com/lizhemin15/NeurIPS-2026-Latex-Unified/main/neurips_2026.sty
  (a community repository). The file calls itself a "partial rewrite" and adds Chinese and English comments.
* SHA-256: 11660adf0cdf30d40d7d3542b844df675b7f2c19eb632d71dc88b944e8a98ad8
* Retrieved: 2026-10-08 by the build environment. The official download (media.neurips.cc) was blocked by
  the environment's network policy.
* Inspected before use: no \write18, \openout, \directlua or network access. Geometry 5.5in x 9in, Times, lineno
  line numbers in submission mode, "dblblindworkshop" option.

Use: `paper/submission/build.sh proxy` copies this file into a temporary build directory as `neurips_2026.sty` to
approximate the official layout and page count. **Before submission, download the official
Formatting_Instructions_For_NeurIPS_2026.zip, place the official `neurips_2026.sty` in `paper/submission/`, and run
`paper/submission/build.sh official`.**

## Superseded (2026-10-09)
The authors supplied the official `neurips_2026.sty` (`\ProvidesPackage{neurips_2026}[2026-01-29 ...]`, SHA-256
c3fc2894e83d2517ca18b66741d6c595986d97957dc08ec08bb2125a7ec4555a), now at `paper/submission/neurips_2026.sty`.
`paper/final_submission.pdf` is built from it with `build.sh official`. The official file differs from this proxy only
by an extra `education` track option and the absence of an empty-workshop-title warning; all layout parameters
(geometry, fonts, spacing, line numbers, notice) are identical.
