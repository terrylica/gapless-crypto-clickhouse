# Contributing to Gapless Crypto Data

Thank you for your interest in contributing to gapless-crypto-data! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.9+
- [UV package manager](https://docs.astral.sh/uv/getting-started/installation/)
- Git

### Environment Setup

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/terrylica/gapless-crypto-data.git
   cd gapless-crypto-data
   ```

2. **Set up development environment:**

   ```bash
   # Create virtual environment
   uv venv

   # Activate virtual environment
   source .venv/bin/activate  # macOS/Linux
   # .venv\Scripts\activate   # Windows

   # Install dependencies
   uv sync --dev
   ```

3. **Install pre-commit hooks (mandatory):**
   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Before Making Changes

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Verify setup:**

   ```bash
   # Run tests
   uv run pytest

   # Check code formatting
   uv run ruff format --check .

   # Check linting
   uv run ruff check .
   ```

### Making Changes

1. **Code formatting and linting:**

   ```bash
   # Format code
   uv run ruff format .

   # Fix linting issues
   uv run ruff check --fix .

   # Type checking
   uv run mypy src/
   ```

2. **Running tests:**

   ```bash
   # Run all tests
   uv run pytest

   # Run specific test file
   uv run pytest tests/test_specific.py -v

   # Run with coverage
   uv run pytest --cov=src/gapless_crypto_data
   ```

3. **Pre-commit validation:**
   ```bash
   # Run all pre-commit hooks
   uv run pre-commit run --all-files
   ```

## Code Standards

### Code Style

- **Formatting**: Code is automatically formatted using Ruff
- **Linting**: All code must pass Ruff linting checks
- **Type hints**: Use type hints for all public APIs
- **Docstrings**: Follow Google-style docstrings for all public functions and classes

### Testing

- **Test coverage**: Aim for high test coverage on new features
- **Test structure**: Place tests in `tests/` directory
- **Test data**: Use fixtures in `tests/fixtures/` for test data
- **Async tests**: Mark async tests with `@pytest.mark.asyncio`

### Documentation

- **API documentation**: Update docstrings for any API changes
- **README updates**: Update README.md if adding new features
- **Changelog**: Add entries to CHANGELOG.md for significant changes

## Submitting Changes

### Pull Request Process

1. **Ensure all checks pass:**

   ```bash
   uv run pytest
   uv run ruff format --check .
   uv run ruff check .
   uv run mypy src/
   uv run pre-commit run --all-files
   ```

2. **Commit changes:**

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

3. **Push to your fork:**

   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create pull request:**
   - Navigate to the GitHub repository
   - Click "New Pull Request"
   - Provide clear description of changes
   - Reference any related issues

### Commit Message Format

Use conventional commit format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:

```
feat: add concurrent download manager
fix: resolve gap detection edge case
docs: update API documentation
test: add tests for hybrid URL generator
```

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Environment details**: Python version, OS, package version
- **Reproduction steps**: Clear steps to reproduce the issue
- **Expected vs actual behavior**: What you expected vs what happened
- **Error messages**: Include full error messages and stack traces
- **Sample code**: Minimal code that reproduces the issue

### Feature Requests

For feature requests, please include:

- **Use case**: Describe the problem you're trying to solve
- **Proposed solution**: Your suggested approach
- **Alternatives considered**: Other solutions you've considered
- **Additional context**: Any other relevant information

## Code Review Process

### Review Criteria

Pull requests are reviewed for:

- **Functionality**: Does the code work as intended?
- **Code quality**: Is the code well-structured and maintainable?
- **Tests**: Are there adequate tests for the changes?
- **Documentation**: Is documentation updated appropriately?
- **Compatibility**: Does it maintain backward compatibility?

### Review Timeline

- **Initial review**: Within 1-2 business days
- **Follow-up**: Based on complexity and reviewer availability
- **Merge**: After approval and passing all checks

## Development Guidelines

### Adding New Features

1. **Design**: Consider the API design and backward compatibility
2. **Implementation**: Follow existing patterns and conventions
3. **Testing**: Add comprehensive tests for new functionality
4. **Documentation**: Update relevant documentation
5. **Examples**: Add usage examples if appropriate

### Performance Considerations

- **Efficiency**: Consider performance implications of changes
- **Memory usage**: Be mindful of memory consumption
- **Concurrency**: Ensure thread safety where applicable
- **Testing**: Include performance tests for critical paths

### Security Considerations

- **Input validation**: Validate all user inputs
- **Data handling**: Handle sensitive data appropriately
- **Dependencies**: Keep dependencies up to date
- **Secrets**: Never commit secrets or API keys

## Getting Help

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: technical questions to terry@eonlabs.com

### Resources

- **Documentation**: [Project README](README.md)
- **API Reference**: See docstrings in source code
- **Examples**: Check `examples/` directory
- **Tests**: Review existing tests for usage patterns

## License

By contributing to gapless-crypto-data, you agree that your contributions will be licensed under the MIT License.
