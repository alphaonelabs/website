# Contributing to BotLab

BotLab is part of the [Alpha One Labs website monorepo](https://github.com/alphaonelabs/website). Keep changes focused on the `botlab/` project and follow the repository's [contributing guidelines](../CONTRIBUTING.md) and [Code of Conduct](../CODE_OF_CONDUCT.md).

## Find an issue

Browse [open BotLab issues](https://github.com/alphaonelabs/website/issues?q=is%3Aissue+is%3Aopen+label%3A%22project%3A+botlab%22). If you are proposing new work, open an issue and add the `project: botlab` label before starting.

## Development setup

Fork `alphaonelabs/website`, then clone your fork and enter the BotLab directory:

```bash
git clone https://github.com/YOUR_USERNAME/website.git
cd website/botlab
git remote add upstream https://github.com/alphaonelabs/website.git
```

Run the site locally with Wrangler:

```bash
npx wrangler dev
```

Alternatively, serve the static files with Python 3:

```bash
python3 -m http.server 8000
```

Open the local URL printed by Wrangler, or visit [http://localhost:8000](http://localhost:8000) when using Python. See the [README](README.md) for simulator controls and 3D mode details, and follow [Make and test changes](#make-and-test-changes) for verification instructions.

## Make and test changes

Create a feature branch from the latest `main`:

```bash
git fetch upstream
git switch main
git pull --ff-only upstream main
git switch -c feature/your-feature-name
```

For simulator changes, verify the affected experience in a browser and check the developer console for errors. Gesture controls in the 3D assembler require camera permission in a secure context; keyboard controls are available as a fallback.

## Submit a pull request

Commit your focused changes and push the branch to your fork:

```bash
git add .
git commit -m "docs(botlab): describe local development"
git push origin feature/your-feature-name
```

Open a pull request against `alphaonelabs/website`'s `main` branch. Link the issue, describe the change and how you tested it, and include screenshots when the user interface changes.
