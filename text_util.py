import re

def full2half(text: str) -> str:
    """
    full-width number to half-width
    """
    text = text.replace("\u3000", " ")
    return text.translate(
        str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(94)})
    )


def rename_invalid_filename_characters(text: str, changed: str = " ")->str:
    """
    Convert characters that cannot be used in file names
    """
    return  re.sub(r'[\\|/|:|?|.|"|<|>|\|]', changed, text)
