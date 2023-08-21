def full2half(text: str) -> str:
    """
    full-width number to half-width
    """
    text = text.replace("\u3000", " ")
    return text.translate(
        str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(94)})
    )
