"""Publish the two built-in layouts to the configured database after migration."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import Settings, database
import app.models
import resume_b.models
from resume_b.template_release import publish_templates


if __name__ == '__main__':
    engine, sessions = database(Settings.load().database_url)
    try:
        with sessions.begin() as session:
            result = publish_templates(session)
        print(json.dumps({'published': result}, ensure_ascii=False))
    finally:
        engine.dispose()
