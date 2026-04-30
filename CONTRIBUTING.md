# Contributing to QUVI AI Render (Blender Add-on)

Thank you for your interest in contributing!

## Requirements

- Blender 4.0 or newer
- Python 3.11+ (matches Blender's embedded Python)

## How to Contribute

1. **Fork** this repository
2. **Create a branch** from `main`: `git checkout -b feature/your-feature`
3. **Make your changes**
4. **Open a Pull Request** against `main`

All PRs are reviewed by the maintainer. Please do not merge your own PRs.

## Development Setup

```bash
git clone https://github.com/quvi-ai/blender-plugin
cd blender-plugin
bash scripts/update_vendor.sh ../quviai-python-sdk
```

Then install the `quviai_blender/` directory as a Blender add-on via
Edit > Preferences > Add-ons > Install from Disk.

## Code Guidelines

- No secrets or API keys anywhere in the codebase
- Blender 4.0+ compatible (no deprecated bpy APIs)
- Keep commits atomic and commit messages imperative

## Reporting Bugs

Use [GitHub Issues](../../issues).
For security vulnerabilities, see [SECURITY.md](SECURITY.md).
