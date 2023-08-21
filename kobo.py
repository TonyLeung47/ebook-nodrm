from typing import Literal
import zipfile
from Crypto.Cipher import AES
from Crypto.Util import Padding
import base64
import binascii
import hashlib
from pathlib import Path
from setting import load_setting
import sqlite3
import tempfile
from getmac import get_mac_address
from pydantic import BaseModel
from text_util import full2half
import natsort
import shutil


class KoboBook(BaseModel):
    volumeid: str
    title: str
    path: Path
    type: Literal["kepub", "drm-free"]
    author: str | None = None
    series: str | None = None
    series_number: str | None = None


class Kobo:
    KOBO_HASH_KEYS = ["88b3a2e13", "XzUhGYdFp", "NoCanLook", "QJhwzAtXL"]

    def __init__(self) -> None:
        settings = load_setting()
        self.kobodir = Path(settings.kobo_dir)
        self.bookdir = self.kobodir / "kepub"
        self._books: list[KoboBook] = []
        self._volumeID: list[Path] = []
        self._userkeys: list[bytes] = []

        if not self.exists():
            raise Exception("Kobo not found. You have to set kobo_dir in setting.toml")
        self.connect_db()

    def exists(self) -> bool:
        return self.kobodir.exists()

    def connect_db(self) -> None:
        """copy db file to temp file and read it"""
        kobodb = self.kobodir / "Kobo.sqlite"

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
            except:
                pass
            row = cursor.fetchone()
        return userids

    def getuserkeys(self) -> list[bytes]:
        """get user key from mac address and user id"""
        if len(self._userkeys) != 0:
            return self._userkeys
        userids = self.getuserids()
        macaddr = get_mac_address().upper()
        for hash in self.KOBO_HASH_KEYS:
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

    def decrypt(self, book: KoboBook, output_path: Path) -> None:
        """
        Decrypt the book.

        Args:
            book (KoboBook): book to decrypt
            output_path (Path): output file name. Shold be *.epub
        """
        if book.type == "drm-free":
            return shutil.copy(book.path, output_path)
        user_keys = self.getuserkeys()
        content_keys = self.getcontentKeys(book.volumeid)
        for user_key in user_keys:
            try:
                self.RemoveDrm(book.path, output_path, user_key, content_keys)
                return
            except:
                pass

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
                        type="kepub",
                        author=row[2],
                        series=row[3],
                        series_number=row[4],
                    )
                )
                self._volumeID.append(row[0])
        """Drm-free"""
        for f in self.bookdir.iterdir():
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
                            type="drm-free",
                            author=row[1],
                            series=row[2],
                            series_number=row[3],
                        )
                    )
                    self._volumeID.append(f)
        """Sort"""
        self._books = natsort.natsorted(self._books, key=lambda x: x.title)
        return self._books

    @property
    def book_names(self) -> list[str]:
        """The list of book names in the library."""
        return [book.title for book in self.books]

    def __bookfile(self, volumeid: str) -> Path:
        """The filename needed to open a given book."""
        return self.kobodir / "kepub" / volumeid

    @staticmethod
    def __DecryptContents(
        contents: bytes, user_key: bytes, contentKeyBase64: str
    ) -> bytes:
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
                        contents = Kobo.__DecryptContents(
                            contents, user_key, contentKeyBase64
                        )
                    outputZip.writestr(filename, contents)
