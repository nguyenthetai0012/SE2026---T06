"""Security tests added in C4 for problem P3 (BOLA + data exposure)."""

import json
import unittest

from tests.ad023.helpers import DAY13, history, overview, seeded_app
from ad023.core.auth import AccessDenied, Principal

ONLY_A = Principal("u-a", frozenset({"BLD-A"}))
NOBODY = Principal("u-none", frozenset())


class BuildingAuthorization(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_scoped_user_reads_own_building(self):
        self.assertEqual(overview(self.app, "BLD-A", DAY13, principal=ONLY_A)["value"], 4.5)

    def test_bola_other_building_overview_denied(self):
        with self.assertRaises(AccessDenied):
            overview(self.app, "BLD-B", DAY13, principal=ONLY_A)

    def test_bola_device_of_other_building_denied(self):
        with self.assertRaises(AccessDenied):
            history(self.app, "METER-03", DAY13, principal=ONLY_A)

    def test_user_without_scopes_denied(self):
        with self.assertRaises(AccessDenied):
            overview(self.app, "BLD-A", DAY13, principal=NOBODY)

    def test_missing_principal_denied(self):
        with self.assertRaises(AccessDenied):
            self.app.dashboard.get_building_overview(None, "BLD-A", *DAY13)

    def test_unknown_device_is_indistinguishable_from_forbidden(self):
        with self.assertRaises(AccessDenied) as unknown:
            history(self.app, "METER-404", DAY13, principal=ONLY_A)
        with self.assertRaises(AccessDenied) as forbidden:
            history(self.app, "METER-03", DAY13, principal=ONLY_A)
        self.assertEqual(str(unknown.exception), str(forbidden.exception))


class DataExposure(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_overview_exposes_only_contract_fields(self):
        result = overview(self.app, "BLD-A", DAY13, principal=ONLY_A)
        self.assertEqual(set(result), {"building_id", "metric", "unit", "window",
                                       "value", "reading_count"})

    def test_no_raw_payload_anywhere_in_responses(self):
        dumped = json.dumps([overview(self.app, "BLD-A", DAY13, principal=ONLY_A),
                             history(self.app, "METER-01", DAY13, principal=ONLY_A)])
        self.assertNotIn("message_id", dumped)
        self.assertNotIn("schema_version", dumped)


class AuditTrail(unittest.TestCase):
    def setUp(self):
        self.app = seeded_app()

    def test_denied_access_is_audited_without_data(self):
        with self.assertRaises(AccessDenied):
            overview(self.app, "BLD-B", DAY13, principal=ONLY_A)
        self.assertEqual(self.app.audit.events, [{
            "outcome": "denied", "action": "building_overview",
            "user_id": "u-a", "target": "BLD-B"}])

    def test_allowed_access_is_not_logged_as_denied(self):
        overview(self.app, "BLD-A", DAY13, principal=ONLY_A)
        self.assertEqual(self.app.audit.events, [])


if __name__ == "__main__":
    unittest.main()
