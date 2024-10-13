from pathlib import Path
from tempfile import TemporaryDirectory

from epub_to_image import epub2cbz
from kindle import KindleBook, KindleProvider
from kobo import KoboBook, KoboProvider
from setting import load_setting
from text_util import rename_invalid_filename_characters


class Ebook:
    def __init__(self) -> None:
        """
        wrapper class for Kobo and Kindle
        """
        self.setting = load_setting()

        # kobo
        try:
            self.kobo = KoboProvider(self.setting)
        except Exception as e:
            print(e)

        # kindle
        try:
            self.kindle = KindleProvider(self.setting)
        except Exception as e:
            print(e)

        self.books = self.kobo.books + self.kindle.books

    def decrypt(self, folder: str | Path, indexes: list[int]) -> None:
        folder = Path(str(folder))
        for index in indexes:
            book = self.books[index]
            title = book.get_title() or "Unknown"
            title = rename_invalid_filename_characters(title)

            if type(book) is KoboBook:
                self.kobo.decrypt(book, folder, name=title)
            elif type(book) is KindleBook:
                self.kindle.decrypt(book, folder, name=title)

    def decrypt_images(self, folder: str | Path, indexes: list[int]) -> None:
        with TemporaryDirectory() as tmpdir:
            self.decrypt(tmpdir, indexes)
            for epub in Path(tmpdir).iterdir():
                if epub.suffix != ".epub":
                    continue
                output_folder = Path(folder) / f"{epub.stem}.cbz"
                epub2cbz(epub, output_folder)


if __name__ == "__main__":
    pass
