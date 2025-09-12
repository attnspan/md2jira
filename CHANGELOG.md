# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-09-12

### 🚨 BREAKING CHANGES
- **Python**: Minimum version requirement increased to Python 3.11+
- **Jira API**: Migration from API v2 to v3 for search operations
- **Issue Types**: Story issue type mapping changed to Task (aligns with standard Jira)

### ✨ Added
- Support for Atlassian Document Format (ADF) in issue descriptions
- Robust retry logic for Jira search indexing delays
- Enhanced issue type mapping with SubTask/Sub-Task variants
- Task issue type support throughout the codebase
- UTF-8 encoding specification for file operations
- Comprehensive test timing and reliability improvements

### 🔧 Changed
- **Dependencies**: Upgraded all dependencies to modern secure versions
  - `certifi`: 2020.12.5 → ≥2023.11.17 (3+ years of security patches)
  - `pytest`: 6.2.5 → ≥7.4.0 (Python 3.11+ support, new features)
  - `urllib3`: 1.26.4 → ≥2.0.0 (HTTP/2, security improvements)
- **API**: Migrated search endpoint from `/rest/api/2/search` to `/rest/api/3/search/jql`
- **Issue Types**: Updated Story → Task throughout codebase and tests
- **File Handling**: Added explicit UTF-8 encoding for better Unicode support

### 🐛 Fixed
- **Critical**: Jira search API returning 410 Gone errors due to deprecation
- **Tests**: Test isolation issues causing intermittent failures
- **Descriptions**: Proper handling of ADF-formatted issue descriptions
- **Regex**: Fixed md2wiki method with proper pattern compilation
- **Dependencies**: Removed duplicate certifi entry in requirements.txt
- **Encoding**: Unicode handling in markdown file parsing

### 🧪 Testing
- All 14 tests now pass consistently (previously 12/14 passing)
- Added timing delays for Jira's asynchronous search indexing
- Improved test assertions for ADF-formatted responses
- Enhanced error handling in test scenarios

### 📚 Documentation
- Updated README.md title for clarity
- Cleaned up example.md with consistent test content  
- Modernized VS Code debug configuration
- Added comprehensive PR template and changelog

### 🔒 Security
- Updated all dependencies to versions with latest security patches
- Improved error handling to prevent information leakage
- Enhanced certificate validation with modern certifi

### ⚡ Performance
- HTTP/2 support via urllib3 2.x
- Better connection pooling and reuse
- Reduced dependency resolution conflicts

### 💔 Deprecated
- Support for Python < 3.11 (due to urllib3 2.x requirement)
- Jira API v2 search endpoint usage (migrated to v3)

### 🗑️ Removed
- Duplicate dependency entries
- Debug files and temporary test data
- Unused import statements

---

## [1.x.x] - Previous Versions

See git history for previous version details.

### Migration Guide

#### From 1.x to 2.0

1. **Environment Setup**:
   ```bash
   # Ensure Python 3.11+
   python --version  # Should be 3.11+
   
   # Update dependencies
   pip install -r requirements.txt
   ```

2. **Jira Compatibility**:
   - Verify your Jira instance supports API v3 (most modern instances do)
   - Test search functionality after upgrade
   - Update any custom integrations that rely on API v2 search

3. **Issue Type Changes**:
   - Existing markdown using Story types will create Task issues
   - Update any automation that expects Story issue types
   - Verify Epic → Task → Subtask hierarchy still works as expected

4. **Testing**:
   ```bash
   # Run full test suite
   python -m pytest test/ -v
   
   # Verify against your Jira instance
   python main.py -i example.md
   ```

#### Rollback Plan

If issues arise, you can temporarily rollback:

```bash
# Revert to Python 3.10 environment
pyenv local 3.10.x

# Install legacy dependencies
pip install certifi==2020.12.5 pytest==6.2.5 urllib3==1.26.4 python-dotenv==1.0.0

# Use previous version
git checkout v1.x.x
```

Note: This will restore the 410 API errors, so plan for permanent migration.
