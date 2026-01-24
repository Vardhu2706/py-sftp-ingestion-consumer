from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (override existing env vars)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

import redis
from rq import SimpleWorker, Queue

listen = ["ai"]
redis_conn = redis.Redis(host="localhost", port=6379)

if __name__ == "__main__":
    queues = [Queue(name, connection=redis_conn) for name in listen]
    worker = SimpleWorker(queues, connection=redis_conn)
    worker.work()
