import redis
from rq import Queue

redis_conn = redis.Redis(host="localhost", port=6379)
ai_queue = Queue("ai", connection=redis_conn, default_timeout=300)