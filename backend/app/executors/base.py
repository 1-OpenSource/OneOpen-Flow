from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class NodeExecutor(ABC):
    node_types: set[str] = set()

    @abstractmethod
    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Execute a node and return a structured result."""


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, NodeExecutor] = {}

    def register(self, executor: NodeExecutor) -> None:
        for node_type in executor.node_types:
            self._executors[node_type] = executor

    def get(self, node_type: str) -> NodeExecutor | None:
        return self._executors.get(node_type)

    def supported_types(self) -> list[str]:
        return sorted(self._executors.keys())


registry = ExecutorRegistry()
