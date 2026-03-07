# Environment Instructions

## Documentation
- Use the documentation:
  - [NiceGUI 3.x](https://nicegui.io/documentation)
  - [Ollama Python](https://github.com/ollama/ollama-python)
  - [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma)
  - [Material Icons](https://fonts.google.com/icons?icon.set=Material+Icons)

## Python
- Use the `python-pro` SKILL to review Python code.
- Always use the `uv` Python environment and package manager for Python:
  - `uv run ...` to execute a Python script.
  - `uvx ...` to run a program directly from PyPI.
  - `uv add ...` to add or manage packages, dependencies, etc.

## NiceGUI 3.x
- Use the latest NiceGUI 3.x for building UIs:
  - Install with: `uv add nicegui`
  - Follow [NiceGUI documentation](https://nicegui.io/documentation) for component usage and best practices.
  - Ensure compatibility with other dependencies (e.g., AG Grid).

## ast-grep
You are operating in an environment where `ast-grep` is installed.
For code searches requiring syntax or structure understanding, use:
```bash
ast-grep --lang [language] -p '<pattern>'
```
Adjust the --lang flag for the specific language. Avoid text-only search tools unless explicitly requested.

## Git Policy

Never perform Git commits, pushes, or any version control operations.
If changes need to be saved or versioned, notify the user and request explicit instructions.

## End of File

Always use UTF-8 with LF line endings for files.
