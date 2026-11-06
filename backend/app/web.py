"""uvicorn 入口：整合 A/B/C 后的完整应用（uvicorn app.web:app）。"""
from app.bootstrap import create_app

app = create_app()
