"""Dashboard module. Depends only on ad023.core abstractions.

C2 resolved P1/P2 (port + single aggregation rule).
C4 resolved P3: every query is authorized per building and raw payloads are
no longer returned (intentional behavior change)."""

from datetime import datetime

from ad023.core.auth import AccessDenied, AuditLog, AuthPolicy, Principal
from ad023.core.ports import UNITS, EnergyQueryPort, Window, round_kwh

LATE_AFTER_SECONDS = 300  # [ĐỀ XUẤT] from MQTT draft PR #10, not approved
_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _seconds_between(earlier, later):
    return (datetime.strptime(later, _FMT) - datetime.strptime(earlier, _FMT)).total_seconds()


class DashboardService:
    def __init__(self, energy: EnergyQueryPort, auth: AuthPolicy, audit: AuditLog):
        self.energy = energy
        self.auth = auth
        self.audit = audit

    def _require(self, principal: Principal, building_id, action, target):
        if building_id is None or not self.auth.can_view_building(principal, building_id):
            self.audit.denied(principal, action, target)
            raise AccessDenied(f"{action} not allowed")

    def get_building_overview(self, principal: Principal, building_id, start, end):
        self._require(principal, building_id, "building_overview", building_id)
        total = self.energy.building_energy(building_id, Window(start, end))
        return {
            "building_id": building_id,
            "metric": "energy_kwh",
            "unit": UNITS["energy_kwh"],
            "window": {"start": start, "end": end},
            "value": round_kwh(total.kwh),
            "reading_count": total.reading_count,
        }

    def get_device_history(self, principal: Principal, device_id, start, end):
        building_id = self.energy.device_building(device_id)
        self._require(principal, building_id, "device_history", device_id)
        return [{
            "event_time": r.event_time,
            "received_at": r.received_at,
            "metric": r.metric,
            "value": r.value,
            "unit": UNITS[r.metric],
            "late": _seconds_between(r.event_time, r.received_at) > LATE_AFTER_SECONDS,
        } for r in self.energy.device_readings(device_id, Window(start, end))]
