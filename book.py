from abc import ABC, abstractmethod
from pathlib import Path


class Book(ABC):
    def get_title(self) -> str | None:
        pass


class BookProvider(ABC):
    @abstractmethod
    def decrypt(self, book: Book, folder: Path, name: str | None):
        pass

    @property
    @abstractmethod
    def books(self) -> list[Book]:
        pass
