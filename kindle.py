from pathlib import Path
from tempfile import TemporaryDirectory

from book import Book, BookProvider
from DeDRM_tools.DeDRM_plugin.k4mobidedrm import decryptBook
from DeDRM_tools.DeDRM_plugin.kindlekey import getkey
from KindleUnpack.lib.kindleunpack import unpackBook
from KindleUnpack.lib.mobi_header import MobiHeader
from KindleUnpack.lib.mobi_sectioner import Sectionizer
from setting import SETTING_FOLDER, Setting
from text_util import full2half

KINDLE_EXTS = [".azw"]


class KindleBook(Book):
    def __init__(self, path: Path, key_path: Path) -> None:
        self.path = path
        self.key_path = key_path

    def decrypt(self, folder: Path, name: str | None):
        """
        decrypt kindle book and convert to epub

        Args:
            book (Path): book to decrypt
            folder (Path): output directory
            name (str | None, optional): output name without suffix. Defaults to None.
        """
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=folder) as tmpdir:
            finished = decryptBook(str(self.path), tmpdir, [str(self.key_path)], [], [], [])
            decrypted = list(Path(tmpdir).glob("**/*"))
            if finished == 1 or len(decrypted) == 0:
                raise FileNotFoundError("Failed to decrypt")

            unpackBook(str(decrypted[0]), tmpdir)
            epub = list(Path(tmpdir).glob("**/*.epub"))[0]
            output_path = folder / f"{name or self.title or self.path.stem}.epub"
            if output_path.exists():
                raise FileExistsError(f"{output_path} already exists")
            epub.rename(output_path)

    def get_title(self) -> str | None:
        try:
            sect = Sectionizer(str(self.path))
            mobi = MobiHeader(sect, 0)
            return full2half(mobi.title)
        except:  # noqa: E722
            return None

    @property
    def title(self) -> str | None:
        return self.get_title()


class KindleProvider(BookProvider):
    def __init__(self, setting: Setting, key_path: Path = SETTING_FOLDER / "kindlekey.k4i") -> None:
        self.dir = Path(setting.kindle_dir)
        self.key_path = key_path
        self._books = None

        if not self.dir.exists():
            raise Exception("Kindle not found. You have to set kindle_dir in setting.toml")
        self.gen_key()

    def gen_key(self) -> None:
        """gen key if not exists"""
        if not self.key_path.exists():
            if not getkey(self.key_path):
                raise Exception("Failed to get kindle key")

    def decrypt(self, book: KindleBook, folder: Path, name: str | None):
        return book.decrypt(folder, name)

    @property
    def books(self) -> list[KindleBook]:
        if self._books is None:
            self._books = [
                KindleBook(book, self.key_path) for book in self.dir.glob("**/*") if book.suffix in KINDLE_EXTS
            ]

        return self._books
