# Contributing Guidelines

## Repository Structure

Keep the repository layout simple and consistent:

- `index.html` — app entry point
- `css/` — stylesheets
- `js/` — JavaScript source modules
- `README.md` and `*.md` docs — project documentation

## Source of Truth Rules

- Keep JavaScript source files only under `js/`.
- Keep stylesheets under `css/`.
- Do **not** add duplicate source files at repository root.

## Documentation Rules

- Use Markdown files with `.md` extensions.
- Use relative links only (no local machine paths like `C:\...` or `file:///...`).

## Hygiene Rules

- Do not commit archives (`*.zip`) or generated artifacts.
- Keep screenshots/reports outside version control unless explicitly needed.
- Follow `.gitignore` and keep it updated when adding new generated outputs.

## Style Checks

After changing code, run:

```bash
npm install
npm run lint
npm run format:check
```
