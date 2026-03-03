# Environment Instructions

## documentation
- Use the documentation:
  - https://nicegui.io/documentation
  - https://github.com/ollama/ollama-python
  - https://github.com/SigmaHQ/pySigma
  - https://fonts.google.com/icons?icon.set=Material+Icons

## python
- use `python-pro` SKILL to review python code
- Always use the `uv` Python environment and package manager for Python.
  - `uv run ...` for running a python script.
  - `uvx ...` for running program directly from a PyPI package.
  - `uv ... ...` for managing environments, installing packages, etc...

## ast-grep
You are operating in an environment where `ast-grep` is installed.
For any code search that requires understanding of syntax or code structure, you should default to using `ast-grep --lang [language] -p '<pattern>'`.
Adjust the `--lang` flag as needed for the specific programming language. Avoid using text-only search tools unless a plain-text search is explicitly requested.

## End of file
- Always use UTF-8 and lf to create or edit text file