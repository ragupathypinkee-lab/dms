"""手动重置演示数据（可选）。首次启动时 init_db 会自动写入 8 条演示需求。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.demo_seed import seed_demo_demands  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402


def run_seed_demo(*, replace_demands: bool = True) -> dict[str, int]:
    init_db()
    with SessionLocal() as db:
        created = seed_demo_demands(db, replace=replace_demands)
        return {"demands": created, "skipped": 0 if created or replace_demands else 1}


if __name__ == "__main__":
    result = run_seed_demo(replace_demands=True)
    if result.get("skipped"):
        print("演示数据已存在，跳过写入（使用 replace_demands=True 可强制重置）")
    else:
        print(f"演示数据写入完成：{result['demands']} 条需求")
