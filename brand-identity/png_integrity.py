"""Validate PNG chunks and scanlines using the Python standard library."""

import struct
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNEL_DEPTHS = {
    0: (1, (1, 2, 4, 8, 16)),
    2: (3, (8, 16)),
    3: (1, (1, 2, 4, 8)),
    4: (2, (8, 16)),
    6: (4, (8, 16)),
}
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def png_chunks(payload):
    if not payload.startswith(SIGNATURE):
        raise ValueError("missing PNG signature")
    offset = len(SIGNATURE)
    while offset < len(payload):
        if len(payload) - offset < 12:
            raise ValueError("truncated PNG chunk")
        size, kind = struct.unpack_from(">I4s", payload, offset)
        end = offset + 8 + size
        if size >= 2**31 or end + 4 > len(payload):
            raise ValueError("invalid PNG chunk length")
        data = payload[offset + 8:end]
        (checksum,) = struct.unpack_from(">I", payload, end)
        if zlib.crc32(data, zlib.crc32(kind)) != checksum:
            raise ValueError(f"{kind!r} chunk CRC mismatch")
        offset = end + 4
        yield kind, data
        if kind == b"IEND":
            if data or offset != len(payload):
                raise ValueError("invalid IEND or trailing PNG data")
            return
    raise ValueError("missing IEND chunk")


def validate_scanlines(compressed, width, height, bits_per_pixel, interlace):
    passes = []
    for x, y, dx, dy in (ADAM7 if interlace else ((0, 0, 1, 1),)):
        columns = (width - x + dx - 1) // dx
        rows = (height - y + dy - 1) // dy
        if columns > 0 and rows > 0:
            passes.append((rows, 1 + (columns * bits_per_pixel + 7) // 8))
    expected = sum(rows * stride for rows, stride in passes)
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(compressed, min(expected + 1, sys.maxsize))
    except zlib.error as error:
        raise ValueError("invalid PNG compressed image data") from error
    if len(pixels) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("PNG image data length does not match the dimensions")
    offset = 0
    for rows, stride in passes:
        end = offset + rows * stride
        if any(filter_type > 4 for filter_type in memoryview(pixels)[offset:end:stride]):
            raise ValueError("invalid PNG scanline filter")
        offset = end


def inspect_png(payload):
    chunks = png_chunks(payload)
    kind, header = next(chunks, (None, b""))
    if kind != b"IHDR" or len(header) != 13:
        raise ValueError("missing or invalid IHDR chunk")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", header)
    if color not in CHANNEL_DEPTHS or not (0 < width < 2**31 and 0 < height < 2**31):
        raise ValueError("invalid PNG dimensions or color type")
    channels, depths = CHANNEL_DEPTHS[color]
    if depth not in depths or compression or filtering or interlace not in (0, 1):
        raise ValueError("unsupported or invalid PNG header fields")

    image_data = bytearray()
    saw_idat = False
    ended_idat = False
    has_palette = False
    for kind, data in chunks:
        if kind == b"IDAT":
            if ended_idat or (color == 3 and not has_palette):
                raise ValueError("invalid IDAT sequence or missing indexed palette")
            saw_idat = True
            image_data.extend(data)
            continue
        ended_idat = saw_idat
        if kind == b"PLTE":
            entries, remainder = divmod(len(data), 3)
            limit = 2**depth if color == 3 else 256
            if has_palette or saw_idat or color in (0, 4) or remainder or not 1 <= entries <= limit:
                raise ValueError("invalid PNG palette")
            has_palette = True
        elif kind != b"IEND" and not kind[0] & 32:
            raise ValueError(f"unexpected critical PNG chunk: {kind!r}")
    if not saw_idat:
        raise ValueError("missing PNG image data")
    validate_scanlines(image_data, width, height, channels * depth, interlace)
    return width, height, color in (4, 6)
