from datetime import datetime, timezone
from threading import RLock


class ExpiringDict:
    def __init__(self) -> None:
        self.entries = {}
        self.expirations = {}

        self.lock = RLock()

    def expire(self):
        with self.lock:
            now = datetime.now(timezone.utc)
            expire_keys = []
            for key, expiration in self.expirations.items():
                if expiration <= now:
                    expire_keys.append(key)

            for key in expire_keys:
                del self.entries[key]
                del self.expirations[key]

    def get(self, key):
        self.expire()
        with self.lock:
            return self.entries.get(key), self.expirations.get(key)

    def put(self, key, value, expiration):
        with self.lock:
            self.expirations[key] = expiration
            self.entries[key] = value
