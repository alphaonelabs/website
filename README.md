<div align="center">

<a href="https://alphaonelabs.com"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/alphaonelabs/.github/main/profile/assets/banner-dark.webp?v=5"><img src="https://raw.githubusercontent.com/alphaonelabs/.github/main/profile/assets/banner-light.webp?v=5" alt="Alpha One Labs. Learn. Share. Explore." width="100%"></picture></a>

# ALPHA ONE LABS

**Open-source education for everyone.** Every Alpha One Labs project lives in this repository, built on one [design system](https://design.alphaonelabs.com).

[learn.alphaonelabs.com](https://learn.alphaonelabs.com) · [GSoC](https://gsoc.alphaonelabs.com) · [Contributing](CONTRIBUTING.md) · [Discussions](https://github.com/orgs/alphaonelabs/discussions)

</div>

## Projects

Each top-level folder is a project. Folders with a live site deploy automatically when they change on `main`.

| Folder | What it is | Live at |
|---|---|---|
| [`learn/`](learn) | Our learning platform: activities, live classrooms, quizzes and payments. Python on Cloudflare Workers, D1 and Durable Objects. | [learn.alphaonelabs.com](https://learn.alphaonelabs.com) and [alphaonelabs.com](https://alphaonelabs.com) |
| [`virtual/`](virtual) | A 3D virtual world built with three.js | [virtual.alphaonelabs.com](https://virtual.alphaonelabs.com) |
| [`quantalab/`](quantalab) | Physics, chemistry and biology simulations with an AI mentor | [quantalab.alphaonelabs.com](https://quantalab.alphaonelabs.com) |
| [`botlab/`](botlab) | A virtual robotics playground | [botlab.alphaonelabs.com](https://botlab.alphaonelabs.com) |
| [`voxbridge/`](voxbridge) | AI accessibility tools: captions, sign-to-speech and scene description | [voxbridge.alphaonelabs.com](https://voxbridge.alphaonelabs.com) |
| [`earthmind/`](earthmind) | Environmental data monitoring with anomaly detection | [earthmind.alphaonelabs.com](https://earthmind.alphaonelabs.com) |
| [`pmoss/`](pmoss) | Open-source project management on GitHub Issues | [pmoss.alphaonelabs.com](https://pmoss.alphaonelabs.com) |
| [`mockuper/`](mockuper) | Quick mockups in the browser | [mockuper.alphaonelabs.com](https://mockuper.alphaonelabs.com) |
| [`gsoc/`](gsoc) | Google Summer of Code: guide, leaderboard and [project ideas](https://gsoc.alphaonelabs.com/ideas) | [gsoc.alphaonelabs.com](https://gsoc.alphaonelabs.com) |
| [`app/`](app) | The Flutter education app | — |
| [`design-system/`](design-system) | Shared UI and brand | — |
| [`learnpilot/`](learnpilot), [`scholarai/`](scholarai), [`syntharia/`](syntharia), [`virtual-labs/`](virtual-labs) | Projects in early planning (see [GSoC ideas](https://gsoc.alphaonelabs.com/ideas)) | — |
| [`website-django/`](website-django) | The original Django site. **Retired**, kept for reference. | — |

## Getting started

```bash
git clone https://github.com/alphaonelabs/website.git
cd website/learn        # or any project folder
```

Each project's README explains how to run it locally.

## How deploys work

Pushing to `main` runs [`deploy-sites.yml`](.github/workflows/deploy-sites.yml), which deploys every changed folder that contains a `wrangler.toml`. A new project gets its own subdomain automatically: add a `wrangler.toml` to `myproject/` and it goes live at `myproject.alphaonelabs.com`.

## History

Each project was its own repository until November 2026. Their full commit histories were merged into their folders here, so `git log -- <folder>` and blame go all the way back. Tags from those repos are prefixed with the folder name, for example `mockuper/v1.0`.

## License

See [LICENSE](LICENSE) and each project's own license file.
