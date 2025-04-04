# Contributing to Telegram MCP

Thank you for your interest in contributing to the Telegram MCP project! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment** by following the instructions in the README.md

## Development Process

1. **Create a feature branch** from the main branch
2. **Make your changes** and commit them with descriptive commit messages
3. **Test your changes** thoroughly
4. **Push your branch** to your fork on GitHub
5. **Submit a pull request** to the main repository

## Coding Standards

- Follow PEP 8 style guidelines for Python code
- Include type hints for all function parameters and return values
- Write comprehensive docstrings for all modules, classes, and functions
- Use meaningful variable and function names


## Pull Request Guidelines

- Provide a clear description of the changes in your PR
- Link any related issues
- Keep PRs focused on a single feature or bug fix
- Ensure your code passes all tests and linting checks

## Feature Requests

If you have an idea for a new feature:

1. Check existing issues to see if it has already been suggested
2. Create a new issue with the "feature request" label
3. Include a detailed description of the feature and its use cases

## Bug Reports

When reporting a bug:

1. Check existing issues to avoid duplicates
2. Include detailed steps to reproduce the issue
3. Describe the expected vs. actual behavior
4. Include information about your environment (OS, Python version, etc.)

## Project Structure

The project is organized as follows:

- `telegram-bridge/`: Python application that connects to Telegram's API
- `telegram-mcp-server/`: MCP server implementation exposing Telegram tools
- `run_telegram_server.sh`: Convenient script for running the server

## Future Roadmap

The project's roadmap includes:
- Adding message threading support
- Improving multimedia message handling
- Adding support for editing messages
- Creating a web UI for configuration and monitoring
- Enhancing error handling and recovery

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Questions?

If you have any questions about contributing, feel free to open an issue or reach out to the maintainers directly.

Thank you for your contributions!