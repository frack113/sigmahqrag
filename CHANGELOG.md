# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-02

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
