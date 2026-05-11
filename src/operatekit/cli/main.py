from __future__ import annotations

import argparse
import json
from pathlib import Path

from operatekit import AutomationSDK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opkit")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run-flow")
    run.add_argument("flow", help="FlowSpec JSON file")
    run.add_argument("--platform", choices=["android", "windows"], required=True)
    run.add_argument("--package")
    run.add_argument("--serial")
    run.add_argument("--executable")
    run.add_argument("--title")
    run.add_argument("--backend", default="uia")
    run.add_argument("--artifacts-dir", default="./artifacts")
    args = parser.parse_args(argv)

    if args.cmd == "run-flow":
        flow = json.loads(Path(args.flow).read_text(encoding="utf-8"))
        if args.platform == "android":
            sdk = AutomationSDK.create_android(package=args.package, serial=args.serial, artifacts_dir=args.artifacts_dir)
        else:
            sdk = AutomationSDK.create_windows(executable=args.executable, title=args.title, backend=args.backend, artifacts_dir=args.artifacts_dir)
        result = sdk.run_flow_spec(flow, raise_on_failure=False)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.status.value == "passed" else 1
    return 1
