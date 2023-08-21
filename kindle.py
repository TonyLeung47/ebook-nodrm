from DeDRM_tools.DeDRM_plugin.kindlekey import getkey
from DeDRM_tools.DeDRM_plugin.k4mobidedrm import decryptBook
from KindleUnpack.lib.mobi_sectioner import Sectionizer
from KindleUnpack.lib.mobi_header import MobiHeader
from KindleUnpack.lib.kindleunpack import unpackBook
from text_util import full2half
from tempfile import TemporaryDirectory
from setting import load_setting
from pathlib import Path


class Kindle:
    KINDLE_KEY = Path(__file__).parent / "kindlekey.k4i"
    KINDLE_EXT = [".azw"]

    def __init__(self) -> None:
        settings = load_setting()
        self.kindledir = Path(settings.kindle_dir)

        if not self.exists():
            raise Exception(
                "Kindle not found. You have to set kindle_dir in setting.toml"
            )
        self.gen_key()

    def exists(self) -> bool:
        return self.kindledir.exists()

    def decrypt_epub(
        self, book: Path, folder: Path, output_name: str | None = None
    ) -> bool:
        """
        decrypt kindle book and convert to epub

        Args:
            book (Path): book to decrypt
            folder (Path): output directory
            output_name (str | None, optional): output name withou suffix. Defaults to None.

        Returns:
            bool: True if success
        """
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        with TemporaryDirectory(dir=folder) as tmpdir:
            finished = decryptBook(
                str(book), tmpdir, [str(self.KINDLE_KEY)], [], [], []
            )

            decrypted = list(Path(tmpdir).glob("**/*"))
            if finished == 1 or len(decrypted) == 0:
                return False
            unpackBook(str(decrypted[0]), tmpdir)

            epub = list(Path(tmpdir).glob("**/*.epub"))[0]
            output_path = folder / f"{output_name or book.stem}.epub"
            if output_path.exists():
                return False
            epub.rename(output_path)
            return True

    def gen_key(self) -> None:
        """gen key if not exists"""
        if not self.KINDLE_KEY.exists():
            if not getkey(self.KINDLE_KEY):
                raise Exception("Failed to get kindle key")

    @property
    def books(self) -> list[Path]:
        return [
            book
            for book in self.kindledir.glob("**/*")
            if book.suffix in self.KINDLE_EXT
        ]

    def get_title(self, azwpath: str | Path) -> str | None:
        try:
            sect = Sectionizer(str(azwpath))
            mobi = MobiHeader(sect, 0)
            return full2half(mobi.title)
        except:
            return None
