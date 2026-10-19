# APP-05 Smart Campus Energy Dashboard — Test Plan
## 1. Purpose
This document defines the initial testing plan for the APP-05 Smart Campus Energy Dashboard. It identifies the major test areas, test scenarios, input conditions, expected results, and proposed continuous integration (CI) checks.

The project is at the initial planning stage. Test scenarios will be refined when the team agrees on the system architecture, data contracts, technology stack, and acceptance criteria.

## 2. Scope

Testing will cover the following areas:

- MQTT data ingestion and payload validation.
- Device registration and device status.
- Offline device detection and recovery.
- Energy alerts and abnormal readings.
- Historical time-series queries.
- Dashboard data display and updates.
- Late, out-of-order, and duplicate messages.
- Performance and load handling.
- Basic security and configuration checks.

## 3. Test Strategy

The team should use a combination of the following testing methods:

- **Unit testing:** Verify individual functions, such as payload validation and alert-condition evaluation.
- **Integration testing:** Verify communication between ingestion, storage, alert processing, and other system components.
- **API or contract testing:** Verify that inputs, outputs, and error responses follow the contracts approved by the team.
- **End-to-end testing:** Verify important user workflows from incoming sensor data to dashboard display and alert presentation.
- **Performance testing:** Measure system behavior under an agreed message rate and data volume.
- **Security testing:** Check input validation, access control where applicable, secret handling, and error responses.

The implementation language and testing framework have not yet been finalized. Specific tools should be selected after the team confirms the technology stack.

## 4. Test Environment and Preconditions

Before executing the tests, the team should agree on:

- The application architecture and supported interfaces.
- The MQTT topic structure and message schema.
- Required sensor fields, units, timestamps, and validation rules.
- Device registration and identification rules.
- The policy for duplicate, late, and out-of-order messages.
- Offline detection thresholds and recovery behavior.
- Alert thresholds and alert-clearing rules.
- Historical query limits and timezone conventions.
- Expected concurrent devices, message rate, and performance targets.

Tests should use a controlled environment and synthetic sensor data. Production credentials and real sensitive data must not be used.

## 5. Test Matrix

| ID | Area | Test scenario | Verification method |
|---|---|---|---|
| TC-01 | Ingestion | Submit a valid sensor message | Integration test: verify the message is accepted and processed according to the approved contract |
| TC-02 | Ingestion | Submit a message with a missing required field | Contract test: verify the message is rejected or handled according to the approved validation rules |
| TC-03 | Ingestion | Submit a message with an invalid data type or unit | Contract test: verify invalid data does not silently become a valid reading |
| TC-04 | Device registry | Submit data from an unknown device | Integration test: verify behavior follows the approved device-registration policy |
| TC-05 | Device status | Stop sending messages from a registered device | Integration test: verify the device becomes offline according to the agreed timeout |
| TC-06 | Device status | Resume messages from an offline device | Integration test: verify recovery follows the approved status-transition policy |
| TC-07 | Alerts | Submit a reading above an agreed alert threshold | Integration test: verify the expected alert is generated |
| TC-08 | Alerts | Submit a reading below the alert threshold | Integration test: verify no new threshold-based alert is generated unless another rule applies |
| TC-09 | History | Query readings for a valid time range | API/integration test: verify returned readings and timestamps match the stored data |
| TC-10 | History | Query an invalid or reversed time range | API test: verify the request is validated and an appropriate response is returned |
| TC-11 | Dashboard | Display available device readings and statuses | End-to-end test: compare the displayed values and statuses with known test data |
| TC-12 | Dashboard | Refresh or update incoming readings | End-to-end test: verify the dashboard reflects new data according to the agreed update behavior |
| TC-13 | Data ordering | Deliver readings out of timestamp order | Integration test: verify storage and query results follow the agreed ordering policy |
| TC-14 | Data timeliness | Deliver a reading later than the normal arrival time | Integration test: verify late data follows the approved acceptance and alert policy |
| TC-15 | Duplicate handling | Deliver the same message more than once | Integration test: verify duplicate handling follows the agreed deduplication policy |
| TC-16 | Load | Increase the incoming message rate to an agreed target | Performance test: measure throughput, latency, errors, and resource use |
| TC-17 | Security | Submit malformed or unexpectedly large payloads | Security/integration test: verify safe handling without crashes or uncontrolled resource use |
| TC-18 | Configuration | Start a component with required configuration missing | Startup test: verify a clear error is reported and secrets are not exposed |

## 6. Detailed Edge-Case Scenarios

### 6.1 Late and Out-of-Order Data

**Input:**

1. Submit reading A for device D1 with event timestamp 10:00.
2. Submit reading B for device D1 with event timestamp 10:02.
3. Submit reading C for device D1 with event timestamp 10:01 after reading B has already arrived.

**Expected result:**

- The system processes the messages according to the team's approved event-time and arrival-time policy.
- Historical queries return readings in the agreed order.
- A late reading does not silently overwrite a newer reading unless that behavior is explicitly specified.
- Alert evaluation follows the agreed policy for late readings.

**Open decision:** The team must define whether late data is accepted, rejected, or stored with a late-data indicator, and how it affects alerts.

### 6.2 Offline Device

**Input:**

1. Register device D1.
2. Send valid readings from D1.
3. Stop sending readings for longer than the agreed offline timeout.
4. Resume sending valid readings.

**Expected result:**

- D1 is initially reported as online after valid communication is established.
- D1 is marked offline according to the agreed timeout and status rules.
- D1 recovers according to the agreed reconnection policy.
- The dashboard displays the corresponding device status.

**Open decision:** The offline timeout, heartbeat behavior, and recovery criteria must be agreed by the team.

### 6.3 Load Testing

**Input:**

1. Generate synthetic readings for the agreed number of devices.
2. Increase the message rate in controlled stages.
3. Run each stage for an agreed duration.
4. Record throughput, processing latency, error rate, and resource utilization.

**Expected result:**

- The system is evaluated against measurable performance targets agreed by the team.
- Errors, dropped messages, and processing delays are recorded.
- The test report identifies the tested device count, message rate, duration, and environment.

**Open decision:** The team must define the target device count, message rate, test duration, acceptable error rate, and latency threshold before claiming that the system passes load testing.

## 7. Test Data and Evidence

Use synthetic sensor readings with known device identifiers, values, units, and timestamps.

For each executed test, record:

- Test case ID.
- Environment and software version.
- Input data and relevant configuration.
- Actual result and expected result.
- Pass/fail status.
- Logs, screenshots, or test output where appropriate.
- Defect or issue link when a test fails.

A test must not be marked as passed until it has been executed and its actual result has been checked.

## 8. Initial CI Proposal

After the team confirms the language, framework, and repository commands, GitHub Actions should be configured to run the applicable checks on pull requests and pushes to the agreed branches.

Proposed CI stages:

1. **Checkout:** Retrieve the repository source.
2. **Environment setup:** Install the required runtime and dependencies using the project's documented setup.
3. **Static checks:** Run the agreed formatter, linter, and relevant static analysis.
4. **Unit tests:** Run automated unit tests.
5. **Contract and integration tests:** Run tests that can execute reliably in CI with the required services or test doubles.
6. **Build or validation:** Run the project's documented build or validation command, if applicable.
7. **Test reporting:** Preserve useful test output and failure logs without exposing credentials or sensitive data.

The workflow must use the actual project stack and commands. Do not add a language-specific workflow until the team agrees on the implementation and test framework.

## 9. Security Considerations

- Never commit passwords, tokens, private keys, or production credentials.
- Store required CI secrets in approved GitHub Actions secrets or another approved secret-management system.
- Validate incoming messages before processing them.
- Avoid logging credentials or unnecessary sensitive data.
- Verify authentication and authorization requirements once they are defined.
- Keep test environments isolated from production systems.

## 10. Risks and Open Questions

The following decisions are required before the test plan can be finalized:

- Which backend, frontend, database, and MQTT broker will be used?
- What is the approved sensor message schema and topic structure?
- How are duplicate messages identified and handled?
- What is the policy for late and out-of-order readings?
- How are alert thresholds and alert recovery defined?
- What timeout determines that a device is offline?
- What historical query limits and timezone rules apply?
- What device count, message rate, latency, and error-rate targets define acceptable performance?
- Which language, test framework, and CI commands will the project use?

## 11. Review and Maintenance

This document is an initial proposal and should be updated as requirements and contracts are approved.

- Backend-related scenarios should be reviewed with Tài.
- Simulator and data-generation scenarios should be reviewed with An.
- The team should confirm the test scope, acceptance criteria, and CI approach before implementation.

Test results and implementation-specific details should be added only after the corresponding tests or checks have actually been performed.

