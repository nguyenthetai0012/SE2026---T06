#!/usr/bin/env python3
"""BT3 VT-023 — thí nghiệm mutation "bỏ idempotency/concurrency guard".

Mỗi mutant được áp vào một git worktree TẠM (detached HEAD), chạy test rồi xoá worktree; nhánh nộp bài
không bao giờ chứa mutant. Diff của mỗi mutant được lưu ở docs/testing/bt3-vt023/mutants/<id>.patch.

    TEST_DATABASE_URL=postgresql+psycopg://USER@localhost:5432/energy_test \
        python tools/scripts/bt3_mutation.py [--repeat 10] [--only M1,M2]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "testing" / "bt3-vt023"
EXPORTS = "src/backend/app/exports.py"
MODELS = "src/backend/app/models.py"
EXPORTS_API = "src/backend/app/exports_api.py"
MIGRATION = "src/backend/alembic/versions/0002_export_api.py"
CONCURRENT = "../../tests/integration/backend/test_export_api.py::test_idempotency_concurrent_retries_create_exactly_one"

MUTANTS = {
    "M1": ("Bỏ ON CONFLICT: kiểm-rồi-chèn ở ứng dụng, vẫn giữ UNIQUE ở DB", [
        (EXPORTS, '            .on_conflict_do_nothing(constraint="uq_exports_client_key")\n', ""),
    ]),
    "M2": ("Bỏ toàn bộ guard: không ON CONFLICT, không UNIQUE (migration và ORM)", [
        (EXPORTS, '            .on_conflict_do_nothing(constraint="uq_exports_client_key")\n', ""),
        (MIGRATION, "            CONSTRAINT uq_exports_client_key UNIQUE (client_id, idempotency_key),\n", ""),
        (MODELS, '        UniqueConstraint("client_id", "idempotency_key", name="uq_exports_client_key"),\n', ""),
    ]),
    "M3": ("Bỏ UNIQUE ở migration nhưng ORM vẫn khai báo (lệch contract ORM <-> DB)", [
        (MIGRATION, "            CONSTRAINT uq_exports_client_key UNIQUE (client_id, idempotency_key),\n", ""),
    ]),
    "M5": ("request_hash bỏ building_id (AI review #3): cùng key, building khác vẫn bị coi là replay", [
        (EXPORTS, '        canon = {"building_id": self.building_id, "metric": self.metric,\n',
         '        canon = {"metric": self.metric,\n'),
    ]),
    "M6": ("Chỉ kiểm scope khi tạo mới (AI review #3): replay sau khi bị thu hồi scope vẫn trả export", [
        (EXPORTS_API, "        if req.building_id not in principal.buildings:\n",
         "        if req.building_id not in principal.buildings and PgExportStore(db).find(principal.client_id, key) is None:\n"),
    ]),
    "M4": ("Replay không so sánh request_hash (cùng key, body khác vẫn trả export cũ)", [
        (EXPORTS, "    if existing.request_hash != want_hash:\n        raise IdempotencyConflict()\n", ""),
    ]),
}

SUMMARY = re.compile(r"(\d+) (passed|failed|error|errors)")


def sh(cmd: list[str], cwd: Path, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def pytest(wt: Path, args: list[str]) -> tuple[dict, list[str], str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    r = sh([sys.executable, "-m", "pytest", "-c", "pyproject.toml", "-p", "no:cacheprovider", "-q", "-rfE", *args],
           wt / "src" / "backend", env)
    counts = {k: int(n) for n, k in SUMMARY.findall(r.stdout.splitlines()[-1] if r.stdout else "")}
    failed = sorted({ln.split(" ", 1)[1].split(" - ")[0] for ln in r.stdout.splitlines()
                     if ln.startswith(("FAILED ", "ERROR ")) and "::" in ln.split(" ", 2)[1]})
    return counts, failed, r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=10, help="số lần chạy lại test đồng thời trên mỗi mutant")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if not os.environ.get("TEST_DATABASE_URL"):
        sys.exit("Cần TEST_DATABASE_URL")
    head = sh(["git", "rev-parse", "--short", "HEAD"], ROOT).stdout.strip()
    (OUT / "mutants").mkdir(parents=True, exist_ok=True)
    results = {"base_commit": head, "mutants": {}}
    for mid, (desc, edits) in MUTANTS.items():
        if a.only and mid not in a.only.split(","):
            continue
        wt = Path(tempfile.mkdtemp(prefix=f"bt3-{mid}-"))
        sh(["git", "worktree", "add", "--detach", str(wt), "HEAD"], ROOT)
        try:
            for f, old, new in edits:
                p = wt / f
                s = p.read_text("utf-8")
                assert s.count(old) == 1, f"{mid}: không tìm thấy đúng một chỗ cần sửa trong {f}"
                p.write_text(s.replace(old, new), "utf-8")
            (OUT / "mutants" / f"{mid}.patch").write_text(sh(["git", "diff"], wt).stdout, "utf-8")
            full_counts, full_failed, _ = pytest(wt, [])
            unit_counts, unit_failed, _ = pytest(wt, ["../../tests/unit/backend"])
            kills, observed = 0, []
            for _ in range(a.repeat):
                c, _, out = pytest(wt, [CONCURRENT])
                if c.get("failed", 0) or c.get("error", 0):
                    kills += 1
                    observed += [ln.strip()[:160] for ln in out.splitlines() if ln.startswith("E ") and "Counter(" in ln][:1]
            results["mutants"][mid] = {
                "description": desc, "full_suite": full_counts, "killed_by": full_failed,
                "unit_tests_with_fake_store": unit_counts,
                "concurrent_test_kill_rate": f"{kills}/{a.repeat}",
                "concurrent_test_observed": observed[:3],
                "status": "KILLED" if full_failed else "SURVIVED",
            }
            print(f"{mid}: {results['mutants'][mid]['status']} full={full_counts} unit={unit_counts} "
                  f"concurrent={kills}/{a.repeat}")
            for t in full_failed:
                print("   ", t)
            for o in observed[:2]:
                print("    observed:", o)
        finally:
            sh(["git", "worktree", "remove", "--force", str(wt)], ROOT)
    (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / "mutation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
