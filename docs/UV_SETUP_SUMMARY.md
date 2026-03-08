# UV Setup Summary

Python environment and dependency management guide for the SigmaHQ RAG application using uv.

## Overview

This guide covers setting up and managing the Python environment for the SigmaHQ RAG application using `uv`, a fast Python package installer and resolver.

## Why Use UV?

- **Speed**: uv is significantly faster than pip for package installation
- **Reliability**: Better dependency resolution and conflict detection
- **Modern**: Built with Rust, designed for modern Python development
- **Compatibility**: Fully compatible with existing Python projects

## Installation

### 1. Install UV

#### Windows
```bash
# Using winget
winget install Astral-sh.uv

# Using pip (fallback)
pip install uv
```

#### macOS
```bash
# Using Homebrew
brew install uv

# Using pip (fallback)
pip install uv
```

#### Linux
```bash
# Using curl
curl --proto '=https' --tlsv1.2 -sSf https://install.python.org/uv | sh

# Using pip (fallback)
pip install uv
```

### 2. Verify Installation

```bash
uv --version
```

Expected output: `uv X.X.X`

## Project Setup

### 1. Clone and Navigate to Project

```bash
git clone https://github.com/frack113/sigmahqrag.git
cd sigmahqrag
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
uv venv

# Activate virtual environment
# Windows
uv run
# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install all dependencies from pyproject.toml
uv sync

# Install in development mode (editable)
uv pip install -e .

# Install specific extras (if defined)
uv pip install -e ".[dev]"
```

## Dependency Management

### 1. Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Add with specific version
uv add package-name==1.2.3

# Add with version constraint
uv add "package-name>=1.0.0,<2.0.0"
```

### 2. Removing Dependencies

```bash
# Remove a dependency
uv remove package-name

# Remove development dependency
uv remove --dev package-name
```

### 3. Updating Dependencies

```bash
# Update all dependencies
uv pip install --upgrade -r requirements.txt

# Update specific package
uv add --upgrade package-name
```

## Project Structure

### pyproject.toml

The project uses `pyproject.toml` for dependency management:

```toml
[project]
name = "sigmahqrag"
version = "2.0.0"
description = "SigmaHQ RAG Application"
dependencies = [
    "nicegui>=3.0.0",
    "chromadb>=0.4.0",
    "openai>=1.0.0",
    "PyPDF2>=3.0.0",
    "python-docx>=0.8.0",
    "Pillow>=10.0.0",
    "easyocr>=1.0.0",
]
```

### requirements.txt

For compatibility with traditional pip workflows:

```
nicegui>=3.0.0
chromadb>=0.4.0
openai>=1.0.0
PyPDF2>=3.0.0
python-docx>=0.8.0
Pillow>=10.0.0
easyocr>=1.0.0
```

## Development Workflow

### 1. Daily Development

```bash
# Activate environment
uv run

# Run the application
uv run python main.py

# Run tests
uv run pytest

# Run linting
uv run ruff check
```

### 2. Adding New Features

```bash
# Create feature branch
git checkout -b feature/new-feature

# Add dependencies if needed
uv add new-package

# Develop your feature
# ...

# Test your changes
uv run pytest

# Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

### 3. Environment Management

```bash
# List installed packages
uv pip list

# Show package information
uv pip show package-name

# Check for outdated packages
uv pip list --outdated

# Clean up unused packages
uv pip check
```

## Common Commands

### Environment Management
```bash
# Create new environment
uv venv

# Remove environment
rm -rf .venv

# List environments
uv venv list
```

### Package Management
```bash
# Install from requirements.txt
uv pip install -r requirements.txt

# Export dependencies
uv pip freeze > requirements.txt

# Install editable package
uv pip install -e .

# Uninstall package
uv pip uninstall package-name
```

### Running Commands
```bash
# Run Python with uv
uv run python script.py

# Run with specific Python version
uv run --python 3.10 python script.py

# Run with environment variables
uv run --env VAR=value python script.py
```

## Troubleshooting

### Common Issues

#### Permission Errors
```bash
# On Unix systems, ensure proper permissions
chmod +x .venv/bin/activate
```

#### Dependency Conflicts
```bash
# Clear cache and reinstall
uv cache clean
uv sync
```

#### Python Version Issues
```bash
# Check Python version
python --version

# Use specific Python version
uv run --python 3.10 python script.py
```

#### Network Issues
```bash
# Use specific index
uv pip install --index-url https://pypi.org/simple package-name

# Use trusted hosts
uv pip install --trusted-host pypi.org package-name
```

### Performance Tips

#### Caching
```bash
# Enable caching
uv cache dir

# Clear cache if needed
uv cache clean
```

#### Parallel Installation
```bash
# Install multiple packages in parallel
uv add package1 package2 package3
```

## Best Practices

### 1. Version Pinning
- Pin exact versions in production
- Use version ranges for development
- Regularly update dependencies

### 2. Environment Isolation
- Always use virtual environments
- Don't install packages globally
- Use separate environments for different projects

### 3. Dependency Management
- Keep dependencies minimal
- Remove unused dependencies
- Document custom configurations

### 4. Development Workflow
- Use feature branches
- Test changes before committing
- Keep pyproject.toml updated

## Migration from pip

### From requirements.txt
```bash
# Convert requirements.txt to pyproject.toml
uv pip install pip-tools
pip-compile requirements.txt
```

### From virtualenv
```bash
# Create new uv environment
cd project-directory
uv venv

# Install dependencies
uv sync
```

## Support

For additional support:

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [SigmaHQ RAG Issues](https://github.com/frack113/sigmahqrag/issues)

## Notes

- Always commit `pyproject.toml` and `uv.lock` to version control
- Use `uv run` for running commands in the virtual environment
- Regularly update uv to the latest version
- Consider using pre-commit hooks for automated dependency management