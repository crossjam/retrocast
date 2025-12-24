# Pytest Warning Filters Explanation

## Overview

This document explains why and how we suppress certain deprecation warnings in our pytest test suite.

## The Warnings

During test execution, you may notice `PendingDeprecationWarning` messages from the `rich-click` library:

```
PendingDeprecationWarning: `use_markdown=` will be deprecated in a future version of rich-click.
Please use `text_markup=` instead.

PendingDeprecationWarning: `use_rich_markup=` will be deprecated in a future version of rich-click.
Please use `text_markup=` instead.

PendingDeprecationWarning: `use_markdown_emoji=` will be deprecated in a future version of rich-click.
Please use `text_markup=` instead.
```

## Root Cause Analysis

### Where Do These Warnings Come From?

These warnings originate from **external dependency code**, not from the retrocast codebase:

1. **Source Library**: `rich-click` version 1.9.4
2. **Dependency Path**: `podcast-archiver` → `rich-click` (transitive dependency)
3. **Specific Location**: `rich_click/cli.py` and `rich_click/rich_help_configuration.py`

### Why Are They Generated?

The rich-click library is in a transitional period where it's migrating from old parameter names to new ones:

**Old parameters (deprecated):**
- `use_markdown=`
- `use_rich_markup=`
- `use_markdown_emoji=`

**New parameter:**
- `text_markup=` (unified replacement)

During this transition, rich-click's own internal code sets both the old and new parameters simultaneously to maintain backward compatibility. This triggers the deprecation warnings in the library's `__post_init__` validation.

### Example from rich-click Source

From `rich_click/cli.py` (line ~136):

```python
cfg.use_markdown = False      # Old parameter (triggers warning)
cfg.use_rich_markup = True    # Old parameter (triggers warning)
cfg.text_markup = "rich"      # New parameter
```

From `rich_click/rich_help_configuration.py`:

```python
@dataclass
class RichHelpConfiguration:
    use_markdown: Optional[bool] = field(default=None)
    use_rich_markup: Optional[bool] = field(default=None)
    text_markup: Optional[str] = field(default=None)

    def __post_init__(self):
        if self.use_markdown is not None:
            warnings.warn(
                "`use_markdown=` will be deprecated in a future version of rich-click."
                " Please use `text_markup=` instead.",
                PendingDeprecationWarning,
                stacklevel=2,
            )
```

## Why We Can't Fix This in Our Code

These warnings are **not caused by anything in the retrocast codebase**:

1. ✅ Our code doesn't import or use `use_markdown` or `use_rich_markup`
2. ✅ Our code doesn't configure rich-click directly with these parameters
3. ✅ The warnings come from rich-click's internal initialization during import
4. ❌ We cannot modify third-party library code

**Verification:**

```bash
# Search retrocast source for deprecated parameters
$ grep -r "use_markdown\|use_rich_markup" src/ tests/
# Result: No matches found
```

The warnings appear because:
- `podcast-archiver` uses `rich-click` for its CLI
- When tests import our CLI (which imports podcast-archiver commands), rich-click initializes
- Rich-click's own code triggers the warnings during initialization

## Solution: Pytest Warning Filters

Since these are external library warnings that we cannot fix, the appropriate solution is to filter them in pytest configuration.

### Implementation

Added to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Filter deprecation warnings from rich-click's internal code
# These warnings are from rich-click's own CLI command, not our code
filterwarnings = [
    "ignore:`use_markdown=` will be deprecated:PendingDeprecationWarning:rich_click",
    "ignore:`use_rich_markup=` will be deprecated:PendingDeprecationWarning:rich_click",
    "ignore:`use_markdown_emoji=` will be deprecated:PendingDeprecationWarning:rich_click",
]
```

### How It Works

The `filterwarnings` configuration uses Python's warning filter syntax:

```
action:message:category:module
```

- **Action**: `ignore` - Suppress the warning
- **Message**: Pattern matching the warning text (e.g., `` `use_markdown=` will be deprecated``)
- **Category**: `PendingDeprecationWarning` - The warning type
- **Module**: `rich_click` - Only filter warnings from this module

This ensures we **only** suppress warnings from `rich_click`, not from our own code or other libraries.

## Why This Approach Is Appropriate

### 1. Specificity
The filters target only the specific warnings from the specific module, not all deprecation warnings.

### 2. Transparency
We can still see warnings when explicitly requested:

```bash
# Show all warnings including filtered ones
$ pytest -W default::PendingDeprecationWarning

# See that warnings are from rich-click
tests/test_cli_quiet_flag.py::test_subcommand_respects_quiet
  <string>:136: PendingDeprecationWarning: `use_markdown=` will be deprecated
```

### 3. Clean Test Output
Normal test runs produce clean output without noise from third-party dependencies:

```bash
$ pytest tests/
============================= test session starts ==============================
84 passed in 14.58s
```

### 4. Proper Scope
The warnings are truly not actionable by us:
- They're from a transitive dependency
- They're from internal library code
- The library itself will fix them in a future release
- There's no configuration we can provide to avoid them

### 5. Documentation
This document provides clear explanation for future maintainers.

## Alternative Approaches Considered

### ❌ Suppress All Deprecation Warnings
```toml
filterwarnings = ["ignore::DeprecationWarning"]
```
**Rejected**: Too broad - would hide warnings from our own code.

### ❌ Upgrade rich-click
```bash
$ uv add rich-click@latest
```
**Not viable**:
- `rich-click` is a transitive dependency of `podcast-archiver`
- Version is controlled by podcast-archiver, not us
- Even latest rich-click (1.9.4) has these warnings during transition

### ❌ Remove podcast-archiver
**Not viable**: Core functionality dependency for episode downloading.

### ❌ Ignore in Code
```python
import warnings
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
```
**Rejected**: Should use pytest configuration for test-specific behavior.

## Verification

### Test That Filters Work

```bash
# Normal run - no warnings
$ pytest tests/test_cli.py -v
17 passed

# Explicit warnings - shows filtered warnings
$ pytest tests/test_cli.py -v -W default::PendingDeprecationWarning
17 passed, 2 warnings

# All tests - clean output
$ pytest tests/ -v
84 passed
```

### Test That Our Code Has No Issues

```bash
# Run with strict warning enforcement for our code
$ pytest tests/ --strict-markers -W error::DeprecationWarning::retrocast
# Would fail if we had deprecation warnings in our code
```

## When to Revisit

These filters should be revisited when:

1. **rich-click releases a new major version** that removes the old parameters
   - Check if warnings are still present
   - Remove filters if no longer needed

2. **podcast-archiver updates its rich-click dependency**
   - Test with filters temporarily removed
   - Keep or remove based on results

3. **We upgrade to a new version of podcast-archiver**
   - Same testing process as above

## Monitoring

To check if these filters are still needed:

```bash
# Temporarily disable filters by commenting them out in pyproject.toml
# Then run:
$ pytest tests/ -W default 2>&1 | grep -i "rich.click"

# If no warnings appear, the filters can be removed
```

## Summary

- **Problem**: PendingDeprecationWarning from rich-click internal code
- **Root Cause**: Transitive dependency (podcast-archiver → rich-click)
- **Not Fixable**: External library issue, not our code
- **Solution**: Pytest filter warnings configuration
- **Result**: Clean test output, warnings still visible when needed
- **Appropriate**: Targeted, documented, and reversible

## References

- [Python Warning Control](https://docs.python.org/3/library/warnings.html)
- [Pytest Warning Capture](https://docs.pytest.org/en/stable/how-to/capture-warnings.html)
- [rich-click Issue Tracker](https://github.com/ewels/rich-click/issues)
- Related commit: `bdfb80a` - Filter rich-click deprecation warnings in pytest
