"""Publish built-in layouts to the configured database after migration."""
import json
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import Settings, database
import app.models
import resume_b.models
from resume_b.template_release import publish_templates
from resume_b.documents import TEMPLATE_NAMES


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', nargs='+', choices=list(TEMPLATE_NAMES), default=None)
    args = parser.parse_args()
    engine, sessions = database(Settings.load().database_url)
    try:
        with sessions.begin() as session:
            result = publish_templates(session, keys=args.templates)
        print(json.dumps({'published': result}, ensure_ascii=False))
    finally:
        engine.dispose()
