# Contributing

Thank you for improving Thai Document Intelligence. Contributions in Thai or English are welcome.

## Development setup

1. Install Python 3.11+, Tesseract 5 with `tha` and `eng` language data, and Node.js 22+.
2. Create a virtual environment and run `pip install -e ".[api,dev]"`.
3. Run `pytest`, `ruff check .`, and `mypy packages/python apps/api apps/worker`.
4. For the web app, run `npm install && npm run build` in `apps/web`.

Use synthetic or openly licensed fixtures only. Never commit real government correspondence, personal data, API keys, or confidential documents.

## Pull requests

- Keep each PR focused on one issue and add tests for behavior changes.
- Preserve field provenance and return `null` instead of guessing missing values.
- Treat public Pydantic models, CLI flags, and `/v1` responses as versioned interfaces.
- Update documentation and `CHANGELOG.md` for user-visible changes.

By participating, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

