#!/usr/bin/env python3
import os
import socket
import time

def wait_for(host, port, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                return True
        except Exception:
            time.sleep(1)
    return False

if __name__ == '__main__':
    redis_url = os.getenv('REDIS_HOST', 'redis').split(':')
    redis_host = redis_url[0]
    redis_port = int(os.getenv('REDIS_PORT', '6379'))

    db_host = os.getenv('POSTGRES_HOST', 'db')
    db_port = int(os.getenv('POSTGRES_PORT', '5432'))

    print(f"Waiting for Redis {redis_host}:{redis_port}")
    if not wait_for(redis_host, redis_port, timeout=60):
        print("Redis not available")
        raise SystemExit(1)

    print(f"Waiting for Postgres {db_host}:{db_port}")
    if not wait_for(db_host, db_port, timeout=60):
        print("Postgres not available")
        raise SystemExit(1)

    print("All services ready")
