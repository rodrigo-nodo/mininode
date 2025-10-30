# Cronómetro minimal: medimos en ms sin decoradores.
import time
def now_ms() -> int: return int(time.perf_counter() * 1000)
def elapsed_ms(start_ms: int) -> int: return int(time.perf_counter() * 1000) - start_ms
