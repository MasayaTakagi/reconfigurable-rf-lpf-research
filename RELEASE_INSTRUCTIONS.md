# GitHub publication instructions / GitHub公開の手順

This directory is a **committed local Git repository**, and the accompanying `.bundle` contains the same Git history. It has **not yet been published** to GitHub. The GitHub integration used to prepare the package can write to *existing* repositories, but cannot create a new repository in the account.

## Create an empty repository using GitHub UI

1. Log in to GitHub and select **New repository** (https://github.com/new).
2. Choose a name such as `reconfigurable-rf-lpf-research`, set **Public** only if you intend to invite open external review, and create the repository **without initializing README or .gitignore**.
3. From a computer with Git, unzip `lpf-review-repository.zip` (or clone the `.bundle`) and run the commands below, replacing `<OWNER>` with the account you choose.

```bash
cd lpf-review-repository
git remote add origin https://github.com/<OWNER>/reconfigurable-rf-lpf-research.git
git push -u origin main
```

The connected GitHub app does *not* authorize publication to any unrelated existing repository. If you want help publishing via the connected GitHub app after creating the empty repo, provide the **full repository URL**. Only publish material you want to make public.

## Verification after publication

- Open the README and verify every link under `docs/` works.
- Confirm repository visibility and that historical experiment data is appropriate to share.
- Run `python scripts/audit_results.py` and verify GitHub Actions `Dataset integrity` passes.
- Add an open review issue from `.github/ISSUE_TEMPLATE/review.md` for the k≈0.98 physical feasibility problem.
- Determine a license before accepting contributions beyond non-distributive review.

## Bundle alternative

```bash
git clone lpf-review-repository.bundle lpf-review-repository
cd lpf-review-repository
git switch main
```
