# Complete Deprecation Plan for `litestar.contrib.sqlalchemy` and `litestar.contrib.repository`

## Summary

This plan outlines the complete removal of BOTH `litestar.contrib.sqlalchemy` AND `litestar.plugins.sqlalchemy` modules for Litestar v3.0. Based on PR #4225, the correct approach is to have users import directly from `advanced_alchemy.extensions.litestar` rather than maintaining any re-export layer in Litestar.

Note: PR #4337 has already been merged, removing `litestar.contrib.repository`.

## Key Understanding from PR #4225

PR #4225 had the right approach but was out of sync with master. The approach was:
- **Remove BOTH** `litestar.contrib.sqlalchemy` AND `litestar.plugins.sqlalchemy` completely
- Users import directly from `advanced_alchemy.extensions.litestar` for all SQLAlchemy functionality
- No re-export layer in Litestar at all - cleaner separation of concerns

## Current State Analysis

### What Still Exists

1. **The entire `litestar/contrib/sqlalchemy/` directory structure** with deprecation warnings

2. **The `litestar/plugins/sqlalchemy.py` file** - this should ALSO be removed based on PR #4225's approach

3. **Test files still importing from wrong locations**:
   - `tests/unit/test_contrib/test_sqlalchemy.py`
   - `tests/e2e/test_advanced_alchemy.py`
   - Various example files

### Previous Attempts

- **PR #3755**: Initial deprecation - added warnings but kept the module (MERGED)
- **PR #4069**: First removal attempt by @provinzkraut (CLOSED)
- **PR #4163**: Second attempt to fix re-export issues by @cofin (OPEN)
- **PR #4225**: Near-perfect implementation, just out of sync (CLOSED)
- **PR #4337**: Remove `litestar.contrib.repository` (MERGED)

## Implementation Plan

### Phase 0: Coordination Strategy

**Recommendation**: Create a fresh branch from latest main, applying the approach from PR #4225

### Phase 1: Create New Branch

```bash
git checkout main
git pull origin main
git checkout -b feat/v3-remove-sqlalchemy-completely
```

### Phase 2: Remove ALL SQLAlchemy modules from Litestar

1. **Delete the contrib.sqlalchemy directory**:
   ```bash
   rm -rf litestar/contrib/sqlalchemy/
   ```

2. **Delete the plugins/sqlalchemy.py file** (important - don't keep any re-export layer):
   ```bash
   rm -f litestar/plugins/sqlalchemy.py
   ```

3. **Clean up any empty repository directories left after PR #4337**:
   ```bash
   rm -rf litestar/contrib/repository/  # Should already be mostly gone, just cleanup
   ```

### Phase 3: Update ALL Imports to Use advanced_alchemy Directly

#### Import Pattern Changes

The migration pattern is:
- `from litestar.contrib.sqlalchemy import X` → `from advanced_alchemy.extensions.litestar import X`
- `from litestar.plugins.sqlalchemy import Y` → `from advanced_alchemy.extensions.litestar import Y`
- `from litestar.plugins.sqlalchemy.base import Z` → `from advanced_alchemy.extensions.litestar.base import Z`

For base classes and mixins:
- `from litestar.plugins.sqlalchemy import base` → `from advanced_alchemy.extensions.litestar import base`

#### Files to Update

1. **Documentation Examples** (`docs/examples/`):
   - `plugins/sqlalchemy/configure.py`
   - `plugins/sqlalchemy/modelling.py`
   - All other SQLAlchemy plugin examples
   - Data transfer object examples using SQLAlchemy

2. **Test Files**:
   - `tests/unit/test_contrib/test_sqlalchemy.py` - Update or delete if testing deprecated functionality
   - `tests/e2e/test_advanced_alchemy.py` - Update imports
   - `tests/examples/test_contrib/test_sqlalchemy/` - Update all imports

3. **Any remaining references in the codebase**

### Phase 4: Update Documentation

1. **Update migration guide** to show the new import pattern
2. **Update any SQLAlchemy references** in the main documentation
3. **Add changelog entry** explaining the breaking change
4. **Update installation docs** to mention installing `advanced-alchemy` for SQLAlchemy support

### Phase 5: Fix Expected Issues

Based on PR #4225, most issues were already resolved. Key things to watch:

1. **Ensure advanced-alchemy is in dependencies** where needed
2. **Update pyproject.toml** if there are any references
3. **Documentation must clearly state** that SQLAlchemy support comes from `advanced-alchemy`

### Phase 6: Testing Strategy

```bash
# Run all tests
make test

# Check type hints
make type-check

# Check linting
make lint

# Build docs
make docs
```

### Phase 7: Create Pull Request

**Commit message**:
```
feat(v3)!: Remove all SQLAlchemy modules in favor of direct advanced-alchemy imports

BREAKING CHANGE: All SQLAlchemy functionality has been removed from Litestar.
Users must now import directly from advanced-alchemy.

Migration:
- from litestar.contrib.sqlalchemy import X → from advanced_alchemy.extensions.litestar import X
- from litestar.plugins.sqlalchemy import Y → from advanced_alchemy.extensions.litestar import Y

This completes the separation of concerns, with advanced-alchemy being the
sole provider of SQLAlchemy integration for Litestar.

Related to:
- #4225 - Previous near-perfect implementation
- #4069, #4163 - Earlier attempts
- #3755 - Original deprecation
```

## Key Differences from Current State

1. **Remove BOTH contrib.sqlalchemy AND plugins.sqlalchemy** - no re-export layer at all
2. **Direct imports from advanced_alchemy** - cleaner, no indirection
3. **Based on PR #4225's approach** which was correct but just needed rebasing

## Success Criteria

- [ ] No SQLAlchemy code remains in Litestar codebase
- [ ] All examples use `advanced_alchemy.extensions.litestar` imports
- [ ] All tests pass with new imports
- [ ] Documentation clearly explains the change
- [ ] No re-export layers or indirection

## Benefits of This Approach

1. **Cleaner separation** - Litestar doesn't maintain SQLAlchemy code
2. **Single source of truth** - advanced-alchemy is the only place for SQLAlchemy integration
3. **Easier maintenance** - No need to keep re-export layers in sync
4. **Clear dependency** - Users know they need advanced-alchemy for SQLAlchemy support

## Timeline

Since PR #4225 already did most of the work, this should be straightforward - mainly rebasing that work on current main. Estimated time: 2-3 hours.