# GitHub publication status / 公開状態

The 214-file engineering review package has been committed to the GitHub repository:

**https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research**

- Default branch: `main`
- Initial package import commit: `808fd3e77087f85ad9ea22d2e31bfb65a2b365b6`
- Repository visibility at initial import: **Private**
- Phase 3 (switched-capacitor code/bit implementation): **on hold pending explicit owner approval**

## Action required to enable external review

The owner should open **Settings → General → Danger Zone → Change repository visibility → Public** if the work is approved for public release. Review all source files and historical ZIPs before changing visibility.

A public repository can be read by anyone. Repository code and data do **not** currently have an owner-approved reuse license; consult [LICENSE-STATUS.md](LICENSE-STATUS.md).

For restricted reviews, keep the repository Private and invite the intended reviewer as a collaborator under **Settings → Collaborators and teams** (label may differ).

## Start reviewing

1. [Requirements](docs/01_requirements_ja.md): all 6 radio band settings, loss and harmonic requirements.
2. [Model](docs/04_model_ja.md): complex load, constant-Q component models, mutual coupling, and IL definition.
3. [Results and evidence](docs/03_results_ja.md), [evidence register](data/evidence_register.csv), [original historical archives](history/original-analysis/).
4. [Reproduction guide](docs/07_reproduction_ja.md) and [audit](scripts/audit_results.py).
5. [Priority questions](docs/06_review_request_ja.md) and [roadmap](docs/05_roadmap_ja.md).

Quick checks:

```bash
python scripts/audit_results.py
python -m unittest discover -s tests -v
```

Use Issues and pull requests with a reproducible model, assumptions, scripts, frequency-domain evidence, and comparison against the current 35 dB nominal harmonic goal.

## Local archive

The packaged ZIP and Git bundle are offline snapshots. For subsequent edits use GitHub directly.

```bash
git clone https://github.com/MasayaTakagi/reconfigurable-rf-lpf-research.git
cd reconfigurable-rf-lpf-research
```
