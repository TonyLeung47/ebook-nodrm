from pathlib import Path
from kobo import Kobo
from kindle import Kindle


class Ebook:
    def __init__(self) -> None:
        """
        wrapper class for Kobo and Kindle
        """
        try:
            self.kobo = Kobo()
            self.kobo_books = self.kobo.books
            self.kobo_book_names = [book.title for book in self.kobo_books]
        except:
            self.kobo_books = []
            self.kobo_book_names = []

        try:
            self.kindle = Kindle()
            self.kindle_books = self.kindle.books
            self.kindle_book_names = [
                self.kindle.get_title(book) or "Can't get title"
                for book in self.kindle_books
            ]
        except:
            self.kindle_books = []
            self.kindle_book_names = []

    @property
    def books(self) -> list[str]:
        """name of books"""
        return self.kobo_book_names + self.kindle_book_names

    def decrypto(self, folder: str | Path, indexes: list[int]) -> None:
        folder = Path(str(folder))
        for index in indexes:
            if index < len(self.kobo_book_names):
                self.kobo.decrypt(
                    self.kobo_books[index],
                    folder / (self.kobo_books[index].title + ".epub"),
                )
            else:
                index = index - len(self.kobo_book_names)
                self.kindle.decrypt_epub(
                    self.kindle_books[index], folder, self.kindle_book_names[index]
                )


if __name__ == "__main__":
    libs = Kobo()
    for book in libs.books:
        libs.decrypt(book, ("unko.epub"))
        break
