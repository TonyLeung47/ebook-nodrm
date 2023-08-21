from pathlib import Path
import tomllib
from pydantic import TypeAdapter, BaseModel


class setting(BaseModel):
    kobo_dir: str
    kindle_dir: str


def load_setting(setting_file: Path | None = None) -> setting:
    if setting_file is None:
        setting_file = Path(__file__).parent / "setting.toml"
    with setting_file.open("rb") as f:
        return TypeAdapter(setting).validate_python(tomllib.load(f))
