\# VT-021 – AI Implementation Plan



\## 1. Objective



Centralize the `OFFLINE\_MULTIPLIER` business configuration so that its value can be changed through an environment variable instead of modifying hard-coded source code.



The default value must remain 3 to preserve existing behavior.



\## 2. Proposed Implementation Steps



1\. Inspect the existing `Settings` class in `app/config.py`.

2\. Add an `offline\_multiplier` setting with a default value of 3.

3\. Load the value from the `OFFLINE\_MULTIPLIER` environment variable.

4\. Validate that the configured value is a positive integer.

5\. Pass the setting from `main.py` to the query functions.

6\. Update `device\_status()` and `is\_stale()` to use the configured multiplier.

7\. Ensure both `list\_devices()` and `building\_summary()` use the same configuration.

8\. Add unit and integration tests for default, valid, and invalid configurations.

9\. Run the existing backend test suite and OpenAPI contract check.

10\. Perform the required mutation test by swallowing an exception and returning default data, then verify that a test detects the defect.



\## 3. Expected Files to Inspect or Modify



| File | Purpose |

|---|---|

| `src/backend/app/config.py` | Centralized configuration and validation |

| `src/backend/app/main.py` | Pass settings to query functions |

| `src/backend/app/queries.py` | Apply the configured multiplier |

| `tests/integration/backend/` | Add behavior and contract tests |

| `docs/contracts/mvp-api.md` | Review whether the documented contract needs updating |



\## 4. Assumptions



\- The default multiplier is 3.

\- The environment variable is read when application settings are initialized.

\- Invalid values must cause explicit configuration failure.

\- The API response structure must remain unchanged.

\- The same multiplier is used for device offline status and data freshness in this implementation.



These assumptions require verification against the assigned VT-021 specification and project-owner decisions.



\## 5. Risks



\- A configuration value may be validated but not passed to every query function.

\- One endpoint may use the configured value while another continues using the old constant.

\- Tests may only check HTTP status codes without checking actual business outcomes.

\- Changing the documented fixed threshold may require contract approval.

\- Existing tests may not detect exception swallowing and default-data responses.



\## 6. Verification Strategy



\- Test default configuration.

\- Test a valid custom multiplier.

\- Test invalid values, including zero, negative numbers, and non-integer strings.

\- Test exact threshold boundaries.

\- Test disabled and unknown device status precedence.

\- Test both device listing and building summary behavior.

\- Test database failure behavior.

\- Run the full backend test suite.

\- Run the OpenAPI contract check.

\- Run the 150-concurrent-user load test and report p95 latency, environment, and limitations.



\## 7. Implementation Constraint



Do not modify source code until the proposed scope and contract changes have been reviewed and approved according to the repository instructions.

