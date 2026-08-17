import time
from threading import Lock


class Throttle:
    """
    Klasa do dławienia programu.
    """

    def __init__(self, rate: int) -> None:
        self.__consume_lock = Lock()
        self.rate = rate
        self.tokens: float = 0.0
        self.last: float | None = None

    def consume(self, amount: int = 1) -> int:
        """
        Na podstawie liczby tokenów określa się, czy można działać, czy czekać.
        """
        with self.__consume_lock:
            now = time.time()

            if self.last is None:
                self.last = now

            elapsed = now - self.last

            if elapsed * self.rate > 1:
                self.tokens += elapsed * self.rate
                self.last = now

            self.tokens = min(self.rate, self.tokens)

            if self.tokens >= amount:
                self.tokens -= amount
                return amount
            return 0
