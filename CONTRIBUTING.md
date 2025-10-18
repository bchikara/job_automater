# Contributing to Job Agent

Thank you for your interest in contributing to Job Agent! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

### Our Standards

- ✅ Be respectful and inclusive
- ✅ Welcome newcomers and help them learn
- ✅ Focus on what is best for the community
- ✅ Show empathy towards other contributors
- ❌ No harassment, trolling, or discriminatory behavior
- ❌ No personal attacks or insults

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/job_agent.git
   cd job_agent
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/job_agent.git
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- MongoDB (local instance)
- LaTeX distribution (for PDF generation)
- Git

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
pip install pytest black flake8 mypy

# Setup configuration
cp .env.example .env
# Edit .env with your test credentials

# Create test resume data
cp base_resume.json.example base_resume.json
cp info/achievements.txt.example info/achievements.txt
```

### Running the Application

```bash
# Run in interactive mode
python cli.py interactive

# Run specific commands
python cli.py config-info
python cli.py validate-config

# Run tests (when available)
pytest tests/
```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

1. **Bug Reports**: Found a bug? Open an issue!
2. **Feature Requests**: Have an idea? Share it!
3. **Code Contributions**: Fix bugs or add features
4. **Documentation**: Improve docs, guides, or comments
5. **Testing**: Add tests or improve coverage
6. **ATS Support**: Add support for new ATS platforms

### Reporting Bugs

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to reproduce**: How to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, MongoDB version
- **Logs**: Relevant log files from `logs/` directory
- **Screenshots**: If applicable

**Template:**

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: macOS 13.0
- Python: 3.10.5
- MongoDB: 6.0.3

## Logs
```
[Paste relevant log entries]
```

## Requesting Features

When requesting features, please include:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've thought of
- **Impact**: Who would benefit from this?

### Code Contributions

#### Finding Issues to Work On

- Check the [Issues](https://github.com/yourusername/job_agent/issues) page
- Look for labels: `good first issue`, `help wanted`, `bug`
- Comment on the issue to let others know you're working on it

#### Making Changes

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write clear, readable code
   - Follow the coding guidelines below
   - Add comments for complex logic
   - Update documentation if needed

3. **Test your changes**:
   - Test manually with the CLI
   - Ensure no regressions
   - Add automated tests if possible

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add support for Workday ATS"
   # or
   git commit -m "fix: resolve MongoDB connection timeout issue"
   ```

   **Commit Message Format**:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `refactor:` Code refactoring
   - `test:` Adding tests
   - `chore:` Maintenance tasks

## Coding Guidelines

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: 120 characters max
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Group by stdlib, third-party, local
- **Docstrings**: Use Google-style docstrings

### Code Style

```python
# Good
def process_job_application(job_data: dict) -> bool:
    """
    Process a job application with automated form filling.

    Args:
        job_data: Dictionary containing job information

    Returns:
        True if application succeeded, False otherwise

    Raises:
        ApplicationError: If critical error during application
    """
    primary_id = job_data.get('primary_identifier')
    logger.info(f"[{primary_id}] Starting application process")

    try:
        # Implementation
        return True
    except Exception as e:
        logger.error(f"[{primary_id}] Application failed: {e}")
        return False
```

### Best Practices

1. **Logging**:
   - Use module-level logger: `logger = logging.getLogger(__name__)`
   - Include job identifier in log messages: `f"[{primary_id}] Message"`
   - Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

2. **Error Handling**:
   - Catch specific exceptions, not bare `except:`
   - Raise custom exceptions for domain-specific errors
   - Always log exceptions with context

3. **Configuration**:
   - Never hardcode credentials or personal info
   - Use environment variables via `config.py`
   - Provide sensible defaults where appropriate

4. **Database**:
   - Always normalize URLs using `database.normalize_url()`
   - Use constants from `config.py` for status values
   - Handle ObjectId serialization properly

5. **AI Integration**:
   - Validate JSON responses from LLM
   - Handle rate limits gracefully
   - Provide fallbacks for AI failures

### Project Structure

```
job_agent/
├── cli.py                 # Main CLI interface
├── config.py              # Configuration management
├── config_validator.py    # Configuration validation
├── setup_wizard.py        # Interactive setup
├── database.py            # MongoDB interface
├── utils.py               # Utility functions
├── job_automator/         # Application automation
│   ├── automator_main.py
│   ├── ats_identifier.py
│   ├── browser_utils.py
│   ├── ats_fillers/       # Platform-specific fillers
│   └── intelligence/      # AI/LLM integration
├── resume_tailor/         # Resume generation
├── document_generator/    # PDF creation
└── scrapers/              # Job scraping
```

## Testing

### Manual Testing

```bash
# Test configuration
python cli.py validate-config
python cli.py config-info

# Test document generation
python cli.py generate-docs --interactive

# Test application flow
python cli.py apply --interactive
```

### Adding Tests

When adding new features, consider adding tests:

```python
# tests/test_your_feature.py
import pytest
from job_automator.ats_identifier import identify_ats

def test_greenhouse_identification():
    """Test that Greenhouse URLs are correctly identified"""
    url = "https://boards.greenhouse.io/company/jobs/123456"
    result = identify_ats(url)
    assert result == "Greenhouse"
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated (if needed)
- [ ] Manually tested the changes
- [ ] No sensitive data in commits
- [ ] Commit messages are clear

### Submitting PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Reference related issues (e.g., "Fixes #123")
   - Describe what changed and why
   - Include testing steps
   - Add screenshots if relevant

3. **PR Template**:
   ```markdown
   ## Description
   Brief description of changes

   ## Related Issue
   Fixes #123

   ## Changes Made
   - Added support for X
   - Fixed bug in Y
   - Updated documentation for Z

   ## Testing
   - [ ] Manually tested feature X
   - [ ] Verified fix for bug Y
   - [ ] Checked backward compatibility

   ## Screenshots (if applicable)
   [Add screenshots here]
   ```

### Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, PR will be merged

### After Merge

```bash
# Update your local repository
git checkout main
git pull upstream main

# Delete your feature branch
git branch -d feature/your-feature-name
```

## Adding New ATS Platform Support

To add support for a new ATS platform:

1. **Identify the platform**:
   - Add URL pattern to `ats_identifier.py`

2. **Create filler class**:
   - Create new file in `job_automator/ats_fillers/`
   - Extend `BaseFiller`
   - Implement required methods

3. **Register the filler**:
   - Add to `ATS_FILLER_MAP` in `automator_main.py`

4. **Test thoroughly**:
   - Test with multiple job postings
   - Handle edge cases
   - Document any platform-specific quirks

5. **Update documentation**:
   - Add to README's supported platforms list
   - Document any special requirements

## Questions?

- Open an issue with the `question` label
- Check existing documentation
- Review CLAUDE.md for architecture details

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Job Agent! 🎉
