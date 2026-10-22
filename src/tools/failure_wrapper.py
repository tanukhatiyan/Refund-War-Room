"""
Refund War Room - Seeded Failure Wrapper.
Injects controlled ~15% simulated failures (timeouts, execution errors, empty results)
for chaos engineering and robustness testing.
"""
import random
from typing import Callable, Any, Dict, Optional


class ToolTimeoutError(Exception):
    """Raised when a simulated tool timeout occurs."""
    pass


class ToolExecutionError(Exception):
    """Raised when a simulated transient tool execution error occurs."""
    pass


class FailureInjector:
    def __init__(self, failure_rate: float = 0.15, seed: Optional[int] = None, enabled: bool = True):
        self.failure_rate = failure_rate
        self.enabled = enabled
        self.rng = random.Random(seed) if seed is not None else random.Random()
        self.invocation_count = 0
        self.injected_failure_count = 0

    def set_seed(self, seed: int):
        self.rng = random.Random(seed)

    def wrap(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Executes the function with probabilistic failure injection."""
        self.invocation_count += 1

        if not self.enabled or self.failure_rate <= 0:
            return func(*args, **kwargs)

        roll = self.rng.random()
        if roll < self.failure_rate:
            self.injected_failure_count += 1
            failure_mode = self.rng.choice(["TIMEOUT", "EXEC_ERROR", "EMPTY_RESULT"])
            
            if failure_mode == "TIMEOUT":
                return {
                    "status": "error",
                    "failure_mode": "TIMEOUT",
                    "error": "ToolTimeoutError: Tool execution timed out after 5000ms (Simulated Failure).",
                    "rows": [],
                    "documents": []
                }
            elif failure_mode == "EXEC_ERROR":
                return {
                    "status": "error",
                    "failure_mode": "EXEC_ERROR",
                    "error": "ToolExecutionError: Transient storage connection failed (Simulated Failure).",
                    "rows": [],
                    "documents": []
                }
            else:  # EMPTY_RESULT
                return {
                    "status": "empty",
                    "failure_mode": "EMPTY_RESULT",
                    "message": "Query completed but returned 0 results (Simulated Empty).",
                    "rows": [],
                    "documents": [],
                    "row_count": 0,
                    "result_hash": None
                }

        # Otherwise execute normally
        return func(*args, **kwargs)


# Global default injector instance
_global_injector = FailureInjector(failure_rate=0.15, seed=42, enabled=False)


def get_failure_injector() -> FailureInjector:
    return _global_injector
