import base64
import binascii
import hashlib
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Literal

import natsort
from Crypto.Cipher import AES
from Crypto.Util import Padding
from getmac import get_mac_address

from book import Book, BookProvider
from setting import Setting
from text_util import full2half

KOBO_HASH_KEYS = ["88b3a2e13", "XzUhGYdFp", "NoCanLook", "QJhwzAtXL"]


class KoboBook(Book):
    def __init__(
        self,
        volumeid: str,
        title: str,
        path: Path,
        drm_type: Literal["kepub", "drm-free"],
        author: str | None = None,
        series: str | None = None,
        series_number: str | None = None,
    ) -> None:
        self.volumeid = volumeid
        self.title = title
        self.path = path
        self.drm_type = drm_type
        self.author = author
        self.series = series
        self.series_number = series_number

    def get_title(self) -> str | None:
        return self.title


class KoboProvider(BookProvider):
    def __init__(self, setting: Setting) -> None:
        self.setting = setting
        self.dir = Path(self.setting.kobo_dir)
        self.book_dir = self.dir / "kepub"
        self._books: list[KoboBook] = []
        self._volumeID: list[Path] = []
        self._userkeys: list[bytes] = []
        if not self.dir.exists():
            raise Exception("Kobo not found. You have to set kobo_dir in setting.toml")
        self.connect_db()

    def connect_db(self) -> None:
        """copy db file to temp file and read it"""
        kobodb = self.dir / "Kobo.sqlite"

        # copy db file to temp file and read it
        self.newdb = tempfile.NamedTemporaryFile(mode="wb", delete=False)
        olddb = open(kobodb, "rb")
        self.newdb.write(olddb.read(18))
        self.newdb.write(b"\x01\x01")
        olddb.read(2)
        self.newdb.write(olddb.read())
        olddb.close()
        self.newdb.close()
        self.__sqlite = sqlite3.connect(self.newdb.name)
        self.__cursor = self.__sqlite.cursor()

    def getuserids(self) -> list[str]:
        """get user id from db"""
        userids = []
        cursor = self.__cursor.execute("SELECT UserID FROM user")
        row = cursor.fetchone()
        while row is not None:
            try:
                userid = row[0]
                userids.append(userid)
            except:  # noqa: E722
                pass
            row = cursor.fetchone()
        return userids

    @property
    def userkeys(self) -> list[bytes]:
        """get user key from mac address and user id"""
        if len(self._userkeys) != 0:
            return self._userkeys
        userids = self.getuserids()
        macaddr = get_mac_address()
        if macaddr is None:
            raise Exception("Failed to get mac address")
        macaddr = macaddr.upper()

        for hash in KOBO_HASH_KEYS:
            hashmacaddr = (hash + macaddr).encode()
            deviceid = hashlib.sha256(hashmacaddr).hexdigest()
            for userid in userids:
                deviceuserid = (deviceid + userid).encode()
                userkey = hashlib.sha256(deviceuserid).hexdigest()
                self._userkeys.append(binascii.a2b_hex(userkey[32:]))

        return self._userkeys

    def getcontentKeys(self, volumeid: str) -> dict[str, str]:
        """get content key from db"""
        content_keys = {
            row[0]: row[1]
            for row in self.__cursor.execute(
                "SELECT elementid,elementkey FROM content_keys,content WHERE volumeid = ? AND volumeid = contentid",
                (volumeid,),
            )
        }
        return content_keys

    @property
    def books(self) -> list[KoboBook]:
        """The list of KoboBook objects in the library."""
        if len(self._books) != 0:
            return self._books
        """Drm-ed kepub"""
        for row in self.__cursor.execute(
            "SELECT DISTINCT volumeid, Title, Attribution, Series,SeriesNumber FROM content_keys, content WHERE contentid = volumeid"
        ):
            if self.__bookfile(row[0]).exists():
                self._books.append(
                    KoboBook(
                        volumeid=row[0],
                        title=full2half(row[1]),
                        path=self.__bookfile(row[0]),
                        drm_type="kepub",
                        author=row[2],
                        series=row[3],
                        series_number=row[4],
                    )
                )
                self._volumeID.append(row[0])
        """Drm-free"""
        for f in self.dir.iterdir():
            if f.name not in self._volumeID:
                row = self.__cursor.execute(
                    f"SELECT Title, Attribution, Series,SeriesNumber FROM content WHERE ContentID = '{f.name}'"
                ).fetchone()
                if row is not None:
                    fTitle = full2half(row[0])
                    self._books.append(
                        KoboBook(
                            volumeid=f.name,
                            title=fTitle,
                            path=self.__bookfile(f.name),
                            drm_type="drm-free",
                            author=row[1],
                            series=row[2],
                            series_number=row[3],
                        )
                    )
                    self._volumeID.append(f)
        """Sort"""
        self._books = natsort.natsorted(self._books, key=lambda x: x.title)
        return self._books

    def __bookfile(self, volumeid: str) -> Path:
        """The filename needed to open a given book."""
        return self.dir / "kepub" / volumeid

    def decrypt(self, book: KoboBook, folder: Path, name: str | None):
        """
        Decrypt the book.

        Args:
            book (KoboBook): book to decrypt
            folder (Path): output directory
            name (str | None, optional): output name without suffix. Defaults to None.
        """
        output_path = folder / f"{name or book.title}.epub"
        if book.drm_type == "drm-free":
            return shutil.copy(book.path, output_path)
        content_keys = self.getcontentKeys(book.volumeid)
        for user_key in self.userkeys:
            try:
                self.RemoveDrm(book.path, output_path, user_key, content_keys)
                return
            except:  # noqa: E722
                pass

    @staticmethod
    def __DecryptContents(contents: bytes, user_key: bytes, contentKeyBase64: str) -> bytes:
        contentKey = base64.b64decode(contentKeyBase64)
        keyAes = AES.new(user_key, AES.MODE_ECB)
        decryptedContentKey = keyAes.decrypt(contentKey)

        contentAes = AES.new(decryptedContentKey, AES.MODE_ECB)
        decryptedContents = contentAes.decrypt(contents)
        return Padding.unpad(decryptedContents, AES.block_size, "pkcs7")

    @staticmethod
    def RemoveDrm(
        inputPath: str | Path,
        outputPath: str | Path,
        user_key: bytes,
        contentKeys: dict[str, str],
    ) -> None:
        with zipfile.ZipFile(inputPath, "r") as inputZip:
            with zipfile.ZipFile(outputPath, "w", zipfile.ZIP_DEFLATED) as outputZip:
                for filename in inputZip.namelist():
                    contents = inputZip.read(filename)
                    contentKeyBase64 = contentKeys.get(filename, None)
                    if contentKeyBase64 is not None:
                        contents = KoboProvider.__DecryptContents(contents, user_key, contentKeyBase64)
                    outputZip.writestr(filename, contents)
