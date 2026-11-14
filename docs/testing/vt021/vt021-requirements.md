# VT-021 – Requirements and Contract



## 1. Problem Statement



The Smart Campus Energy Dashboard currently uses a hard-coded `OFFLINE_MULTIPLIER = 3` in its backend query logic to determine when an enabled device becomes offline.



When the business needs to adjust the offline threshold, developers must modify source code rather than changing a centralized configuration value. This increases maintenance effort and makes future changes harder to verify consistently.



The objective of VT-021 is to centralize the offline multiplier as an environment-based configuration while preserving the existing default behavior and keeping the data freshness rule independent.



## 2. Acceptance Criteria



- **AC-01 – Default configuration:** When `OFFLINE_MULTIPLIER` is not provided, the application uses the default value of 3.

- **AC-02 – Configurable threshold:** When a valid positive integer is provided through `OFFLINE_MULTIPLIER`, the application uses that value for device offline status calculation.

- **AC-03 – Consistent offline calculation:** All device status calculations use the same configured offline multiplier, regardless of the API endpoint that requests the calculation.

- **AC-04 – Configuration validation:** The application rejects non-integer, zero, and negative multiplier values with a clear configuration error.

- **AC-05 – Existing behavior preservation:** Disabled-device precedence, unknown status when `last_seen` is null, the `>=` threshold boundary, API response structure, and the existing data freshness rule remain unchanged.



## 3. Non-functional Requirements



- **NFR-01 – Performance:** Under a load of 150 concurrent users/tasks, the API should achieve a p95 response time of no more than 4.0 seconds in the defined test environment.

- **NFR-02 – Maintainability:** The offline business threshold must be defined and loaded from one centralized configuration source rather than duplicated across query logic.

- **NFR-03 – Reliability:** Database failures must not be swallowed or converted into successful responses containing default or empty data.



## 4. Business Invariants



1. The offline multiplier must be a positive integer.

2. The default offline multiplier is 3.

3. A disabled device has status `disabled`, regardless of its timestamps.

4. An enabled device with `last_seen = null` has status `unknown`.

5. A device is offline when `now - last_seen >= offline_multiplier × period_seconds`.

6. Data is stale when `latest_event_time` is null or `now - latest_event_time >= freshness_multiplier × period_seconds`.

7. The status calculation uses `last_seen`; the freshness calculation uses `latest_event_time`.

8. Changing `OFFLINE_MULTIPLIER` must not change the independent data freshness threshold.

9. Device status and data freshness are separate business outcomes and are not necessarily identical.



## 5. Proposed Contract



The backend loads `OFFLINE_MULTIPLIER` from the environment at application startup.



- Missing variable: use the default value of 3.

- Valid positive integer: use the configured value for device offline status calculation.

- Invalid value: fail application configuration explicitly.

- All device status calculations must use the same configured offline multiplier.

- Data freshness calculations must retain their existing independent threshold and behavior.

- API response fields and the existing error envelope remain unchanged.



**Contract status:** Proposed. Requires review and approval before implementation because the current API documentation specifies a fixed multiplier of 3, while the project baseline distinguishes offline and freshness configuration.


