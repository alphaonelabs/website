# Contributing to Alpha One Labs

Thank you for helping! Everything lives in this one repository, so the steps are the same for every project.

## Workflow

1. **Find or open an issue.** Look for [`good first issue`](https://github.com/alphaonelabs/website/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) to start. Pull requests should link the issue they solve.
2. **Fork and branch.** Fork this repo, then create a branch from `main`.
3. **Work in one project folder.** Keep each PR focused on a single project (`learn/`, `botlab/`, ...). Checks run only for the folders you touch.
4. **Test locally.** Follow the README in the project's folder. For Cloudflare Worker projects, `npx wrangler dev` runs the site locally.
5. **Open a PR** with a clear title and a short description of what changed and how you tested it. Screenshots help for UI changes.

## Where should my change go?

- Most product work belongs in **`learn/`**, our live platform.
- `website-django/` is retired. We don't accept new changes there.
- Want to start a new project? Open a discussion first. Once agreed, a folder with a `wrangler.toml` deploys automatically to `<folder>.alphaonelabs.com`.

## GSoC applicants

See [gsoc.alphaonelabs.com](https://gsoc.alphaonelabs.com) and the [project ideas](https://gsoc.alphaonelabs.com/ideas). Priority goes to applicants with at least five merged PRs.

## Code of Conduct

By taking part you agree to our [Code of Conduct](CODE_OF_CONDUCT.md).
