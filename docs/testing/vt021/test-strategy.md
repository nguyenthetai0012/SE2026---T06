\# VT-021 – Risk-Based Test Strategy



\## 1. Testing Objectives



The purpose of this strategy is to verify that the offline multiplier is configurable, validated, and consistently applied across the relevant API endpoints.



Tests must verify actual business outcomes and API response data rather than relying only on HTTP status codes.



The strategy also verifies that database failures are not swallowed and converted into successful responses containing default data.



\## 2. Risk Assessment



| Risk ID | Risk | Impact | Priority |

|---|---|---|---|

| R-01 | One endpoint uses the configured multiplier while another uses the hard-coded value | Inconsistent business results | High |

| R-02 | Invalid configuration is accepted | Incorrect device status and freshness calculations | High |

| R-03 | Boundary condition uses `>` instead of `>=` | Incorrect status at the exact threshold | High |

| R-04 | Null timestamps or disabled devices are handled incorrectly | Incorrect business status | High |

| R-05 | Database exceptions are swallowed and default data is returned | False successful API responses | Critical |

| R-06 | API response structure changes unintentionally | Contract incompatibility | High |

| R-07 | Performance degrades under concurrent requests | Poor user experience | Medium |



\## 3. Test Data



Use deterministic timestamps and controlled test fixtures.



| Data | Value |

|---|---|

| Reference time (`now`) | 2026-10-27 00:03:00 UTC |

| Device reporting period | 60 seconds |

| Default multiplier | 3 |

| Default offline/freshness threshold | 180 seconds |

| Custom multiplier for testing | 2 |

| Custom threshold | 120 seconds |

| Device enabled state | Both true and false |

| Timestamp cases | Null, below threshold, exactly at threshold, above threshold |



The status calculation must use `last\_seen`, while the freshness calculation must use `latest\_event\_time`. These timestamps must be tested independently.



\## 4. Test Cases



| ID | Layer | Scenario | Expected Result | Priority |

|---|---|---|---|---|

| TC-01 | Unit | Environment variable is missing | Settings use default multiplier 3 | High |

| TC-02 | Unit | Valid positive integer is configured | Settings load the configured value | High |

| TC-03 | Unit / Negative | Multiplier is a non-integer string | Configuration fails explicitly | High |

| TC-04 | Unit / Negative | Multiplier is zero or negative | Configuration fails explicitly | High |

| TC-05 | Unit | Enabled device has `last\_seen` 179 seconds old with multiplier 3 | Status is `online` | High |

| TC-06 | Unit / Boundary | Enabled device has `last\_seen` exactly 180 seconds old | Status is `offline` | Critical |

| TC-07 | Unit | Device is disabled and has an old timestamp | Status is `disabled` | High |

| TC-08 | Unit | Enabled device has `last\_seen = null` | Status is `unknown` | High |

| TC-09 | Unit | `latest\_event\_time` is null | `data\_stale` is true | High |

| TC-10 | Integration / Contract | Custom multiplier 2 is used by device listing | A device aged 120 seconds is reported as offline | Critical |

| TC-11 | Integration / Contract | Custom multiplier 2 is used by building summary freshness calculation | Freshness result follows the 120-second threshold | Critical |

| TC-12 | API / Contract | Successful device and summary responses | Required fields, types, status values, and response structure match the API contract | High |

| TC-13 | Integration / Failure path | Database becomes unavailable during a request | API returns the documented dependency error, not successful empty/default data | Critical |

| TC-14 | Mutation | Temporarily swallow a database exception and return default data | At least one test fails because the returned business data is incorrect or the response incorrectly indicates success | Critical |



\## 5. Test Layers and Rationale



\### Unit Testing



TC-01 to TC-09 verify configuration validation and business invariants independently of the database.



These tests are useful because they isolate threshold calculations, null handling, and status precedence.



\### Integration Testing



TC-10, TC-11, and TC-13 verify that configuration is propagated through the application and that database failures are handled correctly.



Both `list\_devices()` and `building\_summary()` must be covered because both use the freshness/status query logic.



\### API and Contract Testing



TC-12 checks actual response content and structure, not only HTTP status codes.



The test should verify required fields, field types, allowed status values, null behavior, and the existing error envelope where applicable.



The proposed configurable multiplier must also be reconciled with the current API documentation before implementation.



\### Mutation Testing



For TC-14, temporarily introduce a deliberate defect that catches a database exception and returns default or empty data.



Run the relevant tests against the mutated implementation. At least one test must fail for the correct reason.



Restore the correct implementation after the mutation experiment.



\## 6. Non-functional Testing



\### Load Test



\- Target concurrency: 150 concurrent users/tasks.

\- Performance objective: p95 response time ≤ 4.0 seconds.

\- Record the test environment, request count, duration, error rate, and p95 latency.

\- Use representative API requests and controlled test data.

\- Report honestly if the environment cannot sustain the target or if the test harness has limitations.



\### Flaky Test Risk Checks



1\. Use a fixed clock and deterministic timestamps instead of depending on the real current time.

2\. Isolate test data and use the dedicated `energy\_test` database to prevent interference between test runs.



\## 7. Tests Not Prioritized



\- UI visual regression testing: not required for this backend configuration change.

\- MQTT ingestion testing: outside the current implementation scope unless the approved VT-021 specification explicitly includes the MQTT worker.

\- Full end-to-end browser testing: unnecessary for verifying the multiplier calculation when API and integration tests can verify the relevant behavior directly.



\## 8. Test Execution and Evidence



For each test, record:



\- Test ID and requirement/risk covered.

\- Test file and test function.

\- Command executed.

\- Actual result: PASS or FAIL.

\- Evidence such as terminal output or test report.

\- Related implementation commit or pull request.



Do not claim a test passed until it has actually been executed.



\## 9. Current Limitations



This strategy is a proposed test plan. The exact test implementation and final contract assertions depend on confirmation of the VT-021 configuration scope and approval of any required contract changes.

