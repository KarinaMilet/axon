from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def start_scheduler(config: dict, job_fn: callable) -> None:
    scheduler_cfg = config.get("scheduler", {})
    cron_expr = scheduler_cfg.get("cron", "0 8 * * *")
    tz = scheduler_cfg.get("timezone", "UTC")

    trigger = CronTrigger.from_crontab(cron_expr, timezone=tz)

    scheduler = BlockingScheduler()
    scheduler.add_job(job_fn, trigger, name="axon-digest")

    logger.info("Scheduler started — cron='%s', timezone='%s'", cron_expr, tz)
    print(f"Scheduler started. Next run: cron='{cron_expr}', timezone='{tz}'")
    print("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nScheduler stopped.")
