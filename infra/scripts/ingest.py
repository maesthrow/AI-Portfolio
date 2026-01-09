import os
import time
import urllib.request

EXPORT_URL = os.getenv("EXPORT_URL", "http://content-api:8000/api/v1/rag/export")
INGEST_URL = os.getenv("INGEST_URL", "http://rag-api:8000/api/v1/ingest/batch")
RAG_HEALTH_URL = os.getenv("RAG_HEALTH_URL")  # optional

def wait_url(url: str, name: str, timeout: int = 5, sleep_s: int = 2) -> None:
    while True:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                resp.read()
            print(f"{name} OK: {url}")
            return
        except Exception as e:
            print(f"wait {name}: {e}")
            time.sleep(sleep_s)

def main() -> None:
    # ждём пока content-api будет готов отдавать export
    wait_url(EXPORT_URL, "export")

    # опционально ждём health rag-api (если endpoint есть)
    if RAG_HEALTH_URL:
        wait_url(RAG_HEALTH_URL, "rag-health")

    # тянем export payload
    data = urllib.request.urlopen(EXPORT_URL, timeout=30).read()

    # делаем ingest
    req = urllib.request.Request(
        INGEST_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    while True:
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp.read()
            print("RAG ingest done")
            return
        except Exception as e:
            print(f"wait ingest: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
