"""Command-line interface for Muse cron jobs."""
import argparse
import json
import sys
from pathlib import Path
from .core import DataError, init, import_rows, predict, evaluate

def main(argv=None):
    p=argparse.ArgumentParser(prog="muse-keiba")
    sub=p.add_subparsers(dest="command",required=True)
    for command in ("init", "import-entries", "import-history", "import-results", "predict", "evaluate"):
        s=sub.add_parser(command)
        s.add_argument("--db",default="runtime/keiba.sqlite3")
        if command.startswith("import-"):
            s.add_argument("--csv",required=True)
            s.add_argument("--allow-demo",action="store_true")
        if command in ("predict", "evaluate"):
            s.add_argument("--race-id",required=True)
            s.add_argument("--out")
        if command=="predict":
            s.add_argument("--as-of",required=True)
            s.add_argument("--allow-demo",action="store_true")
    a=p.parse_args(argv)
    try:
        if a.command=="init":
            init(a.db)
            obj={"status":"initialized","db":a.db}
        elif a.command.startswith("import-"):
            k=a.command.removeprefix("import-")
            obj={"imported_rows":import_rows(a.db,a.csv,k,a.allow_demo),"kind":k}
        elif a.command=="predict":
            obj=predict(a.db,a.race_id,a.as_of,a.allow_demo)
        else:
            obj=evaluate(a.db,a.race_id)
        data=json.dumps(obj,ensure_ascii=False,indent=2)
        if getattr(a,"out",None):
            target=Path(a.out)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(data+"\n",encoding="utf-8")
        print(data)
        return 0
    except (DataError, OSError) as e:
        print(f"ERROR: {e}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
