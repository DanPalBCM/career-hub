career-hub

Canonical source of truth for Daniel Palacios's career materials: publications,
software, CV, and a small public website.

Everything downstream (the website, the rendered CV PDFs, the LinkedIn sync
checklist) is generated from a handful of files in this repository. Edit the
source files; let CI produce the artifacts.

Website: https://danpalbcm.github.io/career-hub/
Latest CV (PDF): assets/cv/cv-latest.pdf
Contact: Daniel.Palacios@bcm.edu
File layout
career-hub/
├── README.md                  this file
├── CITATION.cff               how to cite this hub
├── LICENSE                    CC BY 4.0 (documentation and CV content)
├── .gitignore
├── publications.bib           CANONICAL publication metadata (edit here only)
├── software.bib               CANONICAL software/repo metadata (edit here only)
├── cv/
│   ├── cv.yaml                CV content for RenderCV (mirrors publications.bib)
│   └── rendercv_settings.yaml CV presentation only (theme, page, margins)
├── assets/
│   ├── cv/                    committed CV PDFs (cv-latest.pdf, cv-YYYY-MM.pdf)
│   └── img/                   images used by the site
├── site/                      Quarto website source
│   ├── _quarto.yml
│   ├── index.qmd
│   ├── publications.qmd       renders from publications.bib
│   ├── software.qmd           renders from software.bib
│   ├── career.qmd
│   └── styles.css
├── tools/
│   └── linkedin_diff.py       prints a manual LinkedIn sync checklist
└── .github/workflows/
    ├── build.yml              render CV + site, deploy to gh-pages
    ├── linkcheck.yml          lychee link check (push + weekly)
    └── scan.yml               gitleaks + inline PHI pattern scan (fail closed)
Update workflow
Edit the source. Publication metadata goes in publications.bib.
Repository metadata goes in software.bib. CV content goes in cv/cv.yaml.
If a publication changes, update publications.bib and the mirroring
entry in cv/cv.yaml in the same commit.
Open a pull request. scan.yml and linkcheck.yml run on the PR and
must pass. build.yml verifies that the CV and the site render.
Merge to main. build.yml re-renders the CV PDFs and the Quarto site
and deploys the site to the gh-pages branch. The refreshed PDFs are
committed back to assets/cv/.
Tag the CV if its content changed: git tag cv-YYYY-MM && git push --tags
(human step; use the year and month of the update).
Sync LinkedIn by hand. Run python tools/linkedin_diff.py > linkedin.md,
open LinkedIn, and work down the checklist. The script generates a checklist
only — it never contacts LinkedIn.
Local preview
bash
python -m pip install "rendercv[full]" "pyyaml" "bibtexparser"
# --pdf-path is relative to the input file (cv/cv.yaml):
rendercv render cv/cv.yaml --design cv/rendercv_settings.yaml \
  --pdf-path ../assets/cv/cv-latest.pdf

# Quarto must be installed separately: https://quarto.org/docs/get-started/
cp -r assets site/assets
quarto preview site/

site/assets/ is a build-time copy and is git-ignored; the committed originals
live in assets/.

Statuses used in publications.bib
keywords value	Meaning
published	Published in a peer-reviewed venue
under-review	Submitted, under review
preprint	Public preprint, not under review at a journal listed here

Under-review manuscripts without a public preprint list metadata only —
title, authors, venue, status. No findings, no numbers.

Never
Never commit PHI, secrets, credentials, or patient-level data. scan.yml
blocks merges on hits, but the scanner is a backstop, not a substitute for
care.
Never edit publication metadata outside publications.bib (and its
mirrored entry in cv/cv.yaml). The site reads from the .bib files so the
pages cannot drift from the canonical record.
Never rename a repository that is cited in a paper. In particular,
clinical-clinpreai-benchmarks is cited in the ClinPreAI manuscript.
Never push to, mirror, or copy anything under LiuzLab/. Those are lab
repositories; this hub links to them and nothing more.
Never add unpublished numbers or claims. Only published papers,
submitted manuscripts, preprints, and the CV are sources for this repo.
Never hide fork status. AMMPER, MedSDoH, OverlapPlots, and
tch-mentormatching are forks or private working copies; software.bib
records that in each entry's note.
Never introduce a paid service. Tooling here is zero-cost.
License

Documentation and CV content in this repository are licensed under
CC BY 4.0. Code in linked repositories carries its own license; see
software.bib.
