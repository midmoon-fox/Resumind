"""Cheap PNG/JPEG dimension gates; A still owns full image validation and access."""

import struct

from .errors import AiFailure
from .schemas import ImagePage


def image_dimensions(page: ImagePage) -> tuple[int, int]:
    data = page.content
    dimensions = None
    if page.mimeType == "image/png":
        if len(data) >= 33 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            if struct.unpack(">I", data[8:12])[0] == 13:
                dimensions = struct.unpack(">II", data[16:24])
    elif data.startswith(b"\xff\xd8\xff"):
        position = 2
        while position < len(data):
            if data[position] != 0xFF:
                break
            while position < len(data) and data[position] == 0xFF:
                position += 1
            if position >= len(data):
                break
            marker = data[position]
            position += 1
            if marker in {0xD9, 0xDA}:
                break
            if marker == 0x01 or 0xD0 <= marker <= 0xD8:
                continue
            if position + 2 > len(data):
                break
            length = int.from_bytes(data[position : position + 2], "big")
            if length < 2 or position + length > len(data):
                break
            if (
                marker
                in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
                and length >= 8
            ):
                height, width = struct.unpack(">HH", data[position + 3 : position + 7])
                dimensions = width, height
                break
            position += length
    if dimensions is None:
        raise AiFailure("OCR_IMAGE_INVALID", "图片格式或尺寸信息无效")
    width, height = dimensions
    if width < 1 or height < 1 or width * height > 20_000_000 or max(width, height) > 8192:
        raise AiFailure("OCR_IMAGE_TOO_LARGE", "图片像素或边长超过识别限制")
    return width, height
