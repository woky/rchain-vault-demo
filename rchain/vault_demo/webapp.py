import asyncio
from typing import Optional

from quart import jsonify, make_response, Quart, render_template, request

app = Quart(__name__)
app.clients = set()

def create_redis():
    url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
    return redis.Redis.from_url(url, decode_responses=True)
