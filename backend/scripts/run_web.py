"""启动 Web 进程：uvicorn app.web:app（整合 A/B/C 的完整应用）"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.web:app", host="0.0.0.0", port=8000, reload=False)
