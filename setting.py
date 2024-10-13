import os
import sys
from pathlib import Path

import tomllib
from pydantic import BaseModel, TypeAdapter

SETTING_FOLDER = Path(sys.argv[0]).parent


class Setting(BaseModel):
    kobo_dir: str
    kindle_dir: str
    default_folder: Path | None = Path(os.getcwd()).parent


def load_setting(setting_file: Path | None = None) -> Setting:
    if setting_file is None:
        setting_file = SETTING_FOLDER / "setting.toml"
    with setting_file.open("rb") as f:
        return TypeAdapter(Setting).validate_python(tomllib.load(f))
