"""Run recovery and Outbox delivery together; factory is operator configuration."""

import argparse
import importlib
import logging
import math
import signal
import threading

from app.modules.tasks.dispatcher import dispatch_pending
from app.modules.tasks.maintenance import recover_due


def run_tick(runtime, publish, *, limit=100):
    result = recover_due(runtime.sessions, runtime.registry, limit=limit)
    result["delivered"] = dispatch_pending(runtime.sessions, publish, limit=limit)
    return result


def run_loop(runtime, publish, *, stop=None, interval=2, limit=100):
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("Supervisor interval must be positive")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Invalid supervisor batch limit")
    stop = stop if stop is not None else threading.Event()
    logger = logging.getLogger(__name__)
    while not stop.is_set():
        try:
            run_tick(runtime, publish, limit=limit)
        except Exception:
            # IDs/errors/DB URLs are not interpolated into general logs.
            logger.error("TASK_SUPERVISOR_TICK_FAILED")
        stop.wait(interval)


def main():
    parser = argparse.ArgumentParser(description="C task recovery and delivery supervisor")
    parser.add_argument(
        "--factory", required=True, help="Trusted module:function -> (runtime, publish)"
    )
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    module, function = args.factory.split(":", 1)
    runtime, publish = getattr(importlib.import_module(module), function)()
    if args.once:
        run_tick(runtime, publish, limit=args.limit)
    else:
        stop = threading.Event()
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        run_loop(runtime, publish, stop=stop, interval=args.interval, limit=args.limit)


if __name__ == "__main__":
    main()
