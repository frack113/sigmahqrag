# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [WIP] - 2026-03-08

### Added
- **LM Studio Integration**: Complete migration from Ollama to LM Studio with custom API compatibility
- **Custom Embeddings**: Created `LMStudioEmbeddings` class for perfect LM Studio API compatibility
- **Optimized Dependencies**: Removed all Ollama dependencies, using only OpenAI-compatible endpoints
- **Comprehensive Testing**: All 4/4 tests passing with custom embeddings working perfectly
- **Code Optimization**: Removed all unused imports and redundant test files
- **Documentation**: Complete project documentation moved to docs folder

### Fixed
- **Embedding API Issues**: Resolved LangChain formatting issues with LM Studio by creating custom embedding wrapper
- **Import Cleanup**: Removed unused `OpenAIEmbeddings` imports from core services
- **Test Consolidation**: Consolidated multiple test files into single comprehensive test
- **Project Structure**: Organized documentation files into proper docs folder structure

### Changed
- **Dependencies**: Updated pyproject.toml to use only OpenAI-compatible dependencies
- **README.md**: Updated to reflect current LM Studio integration and optimized project state
- **Documentation Structure**: Moved all documentation files to docs/ folder for better organization
- **Performance**: Optimized codebase for better performance and cleaner architecture

## [WIP] - 2026-03-02

### Fixed
- **GitHub Repository Management**: Fixed the "URL and Branch are required fields!" error that occurred when trying to add repositories even when all fields were filled. The issue was caused by undefined variables in the `add_repository()` function.
- **UI Cleanup**: Removed redundant "Repository List" label from the repository management page for a cleaner interface
- **Action Buttons**: Temporarily removed edit button from repository table (to be added back in future release)
- **File Cleanup**: Added automatic deletion of repository files on disk when removing repositories from config
- **Duplicate Prevention**: Added validation to prevent adding the same repository with the same branch multiple times
- **Import Error**: Fixed module import issue that was causing 500 error by moving `shutil` import to top level

### Changed
- Updated README.md TODO list to reflect completed fixes and new pending tasks

## [0.1.0] - 2026-03-01

### Added
- Initial implementation of GitHub Repository Management page
- Basic chat interface with document upload capabilities
- Configuration management for GitHub repositories
- Repository addition, removal, and update functionality
- NiceGUI-based responsive UI

### Fixed
- GitHub repository update functionality

## [0.0.1] - 2026-02-22

### Added
- Project scaffolding
- Basic RAG pipeline architecture
- Initial design documents for chat interface and GitHub integration

### Changed
- use of nicegui

## [0.0.0] - 2026-02-22
- Start the projet with js html 
