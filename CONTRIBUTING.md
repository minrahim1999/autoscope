# Contributing to AutoScope

Thanks for your interest in contributing!

## How to contribute

1. **Open an issue first** for bug reports, feature requests, or major changes so we can discuss direction.
2. **Fork the repository** and create a feature branch from `main`.
3. **Make focused, minimal changes.** Prefer deletion over addition; keep code close to the existing style.
4. **Test your changes locally:**
   - Run web tests: `python -m autoscope.cli run --tag web`
   - Run Android tests: `python -m autoscope.cli run --tag android`
   - Launch the desktop app: `python run_desktop.py`
5. **Update the changelog** under `[Unreleased]` if your change is user-facing.
6. **Open a pull request** with a clear description and link to the related issue.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

Make sure `adb` is on your PATH for Android tests.

## Code style

- Use the standard library when possible; keep dependencies minimal.
- Follow the existing file layout and naming conventions.
- Add concise comments only when the code is not self-explanatory.

## Commit messages

Use short, descriptive commit messages in the present tense, e.g.:

- `feat: add android screenshot helper`
- `fix: resolve runner tag filtering on empty suites`
- `docs: update README with Windows install notes`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
