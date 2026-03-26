import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document
from dacke.domain.exceptions import DomainError
from dacke.domain.values.transformer import TransformerSettings

TransformerT = type[Transformer[Any, Document]]


class TransformerRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, TransformerT] = {}

    def register(self, name: str, transformer: TransformerT) -> None:
        self._registry[name] = transformer

    def get(self, name: str) -> TransformerT | None:
        return self._registry.get(name)

    def all(self) -> dict[str, TransformerT]:
        return self._registry.copy()

    def validate(self, transformer: TransformerSettings) -> None:
        if transformer.name not in self._registry:
            raise DomainError(
                "Transformer "
                f"'{transformer.name}' is not registered, "
                f"available transformers: {list(self._registry.keys())}"
            )

    def discover_transformers(
        self,
        package: str | None,
        folder: str = "transformers",
    ) -> None:
        if package is None:
            raise DomainError("Package path is required for transformer discovery")

        current_dir = Path(__file__).parent
        path = current_dir / folder

        if not path.is_dir():
            raise DomainError(f"Transformers directory not found at {path}")

        for _, module_name, _ in pkgutil.iter_modules([str(path)]):
            module = importlib.import_module(f"{package}.{folder}.{module_name}")
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Transformer) and obj is not Transformer:
                    self.register(name, obj)
