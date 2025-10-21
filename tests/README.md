# PARA Autopilot - Test Suite

## 🧪 Test Coverage

This test suite covers critical functionality:

### ✅ Health Checks (`test_health.py`)
- API root endpoint
- Health check endpoint
- Environment configuration

### ✅ Authentication (`test_auth.py`)
- Signup validation (email, password strength)
- Login with credentials
- JWT token validation
- User session management

### ✅ Classification (`test_classification.py`)
- PARA type classification (Project, Area, Resource, Archive)
- Confidence score validation
- AI agent integration
- Edge cases (empty input, invalid data)

### ✅ Scheduling (`test_scheduling.py`)
- Task auto-scheduling logic
- Calendar conflict detection
- Priority-based ordering
- Working hours respect
- Duration validation

---

## 🚀 Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Health checks only
pytest tests/test_health.py

# Auth tests only
pytest tests/test_auth.py -v

# Classification tests only
pytest tests/test_classification.py

# Scheduling tests only
pytest tests/test_scheduling.py
```

### Run with Coverage Report

```bash
pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Only Fast Tests

```bash
pytest -m "not slow"
```

### Run Only Unit Tests

```bash
pytest -m unit
```

---

## 📋 Test Configuration

### Environment Variables

Tests use environment variables from `.env` or fallback to test defaults:

```env
ENVIRONMENT=test
SUPABASE_URL=https://test.supabase.co
ANTHROPIC_API_KEY=test-key
JWT_SECRET=test-secret
```

### Fixtures

Common test fixtures in `conftest.py`:

- `client` - FastAPI test client
- `test_user` - Mock user data
- `test_project` - Mock project data
- `test_task` - Mock task data
- `mock_auth_header` - Mock authentication header

---

## 🎯 Test Scenarios Covered

### Authentication Flow
1. ✅ User signup with validation
2. ✅ Login with email/password
3. ✅ OAuth flow (mocked)
4. ✅ JWT token refresh
5. ✅ Unauthorized access handling

### PARA Classification
1. ✅ Project detection (has deadline, specific outcome)
2. ✅ Area detection (ongoing responsibility)
3. ✅ Resource detection (reference material)
4. ✅ Confidence scoring (0.0-1.0)
5. ✅ Error handling for invalid input

### Task Scheduling
1. ✅ Auto-schedule multiple tasks
2. ✅ Detect calendar conflicts
3. ✅ Respect priority ordering
4. ✅ Respect working hours (8am-6pm)
5. ✅ Handle empty task lists

---

## 🐛 Debugging Failed Tests

### View Detailed Output

```bash
pytest -vv --tb=long
```

### Run Single Test

```bash
pytest tests/test_auth.py::test_signup_validation_weak_password -v
```

### Print Debug Info

```bash
pytest -s  # Shows print() statements
```

---

## 📊 Expected Coverage

Target coverage levels:

- **Critical paths**: 90%+ (auth, classification, scheduling)
- **API endpoints**: 80%+
- **Edge cases**: 70%+
- **Overall**: 75%+

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## ⚠️ Known Limitations

1. **Mocked AI responses** - Claude API calls are mocked, not real
2. **No database integration tests** - Supabase calls are mocked
3. **OAuth flows are partial** - Real OAuth requires browser
4. **Background jobs not tested** - APScheduler tests need separate setup

**For beta testing, run integration tests with real API keys!**

---

## 📝 Adding New Tests

### Template for New Test File

```python
"""Test suite for [feature name]"""

import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def sample_data():
    """Create sample test data"""
    return {"key": "value"}

def test_basic_functionality(client, sample_data):
    """Test basic feature works"""
    response = client.get("/api/endpoint")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_async_functionality(sample_data):
    """Test async feature"""
    result = await some_async_function(sample_data)
    assert result is not None
```

---

**Status**: 🟢 **Ready for Testing**

All critical paths have test coverage. Run `pytest` to verify!
