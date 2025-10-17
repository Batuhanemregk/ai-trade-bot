# Pull Request

## 📋 Description

<!-- Describe your changes in detail -->

## 🎯 Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🧪 Test improvements
- [ ] 🔧 Configuration changes

## 🧪 Testing Done

### Direct Mode Test (Quick):
```bash
# Run this command and paste results
python main.py trading --timeout 300
```

- [ ] Tested with direct mode (5-10 minutes)
- [ ] Logs reviewed, no errors
- [ ] Expected behavior confirmed

### Scheduler Mode Test (Full):
```bash
# Run this for 30-60 minutes
python -m infrastructure.scheduler_runner
```

- [ ] Tested with scheduler mode (30+ minutes)
- [ ] Multiple cycles observed
- [ ] Idempotency verified
- [ ] No job failures

### Unit Tests:
```bash
pytest tests/ -v
```

- [ ] All existing tests pass
- [ ] New tests added (if applicable)
- [ ] Test coverage maintained/improved

## 📊 Test Results

<!-- Paste test output here -->

```
# pytest output
# or scheduler test output
```

## ✅ Checklist

### Code Quality:
- [ ] Code follows SOLID principles
- [ ] Clean Architecture layers respected
- [ ] No unnecessary dependencies added
- [ ] Code is self-documenting with clear names
- [ ] Complex logic has comments

### Testing:
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Smoke tests pass (`pytest -m smoke`)
- [ ] No regression in existing functionality

### Linting:
- [ ] `ruff check .` passes
- [ ] `mypy .` passes (if applicable)
- [ ] Code formatted consistently

### Documentation:
- [ ] README updated (if needed)
- [ ] Docstrings added/updated
- [ ] CHANGELOG.md updated
- [ ] Configuration changes documented

### Scheduler Compatibility:
- [ ] Works in both direct and scheduler modes
- [ ] Idempotency considerations addressed
- [ ] Job execution time reasonable (<30s)
- [ ] No breaking changes to job interface

## 📝 Additional Notes

<!-- Any additional context, screenshots, or notes -->

## 🔗 Related Issues

Closes #<!-- issue number -->

