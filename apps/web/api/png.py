"""Bounded validation of the static PNG profile used for site favicons."""

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FAVICON_BYTES = 1024 * 1024
MAX_FAVICON_DIMENSION = 512
COLOR_DEPTHS = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
ADAM7 = ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
         (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2))


def validate_png(content: bytes) -> tuple[int, int]:
    """Check chunks, checksums, dimensions and bounded pixel-data decoding.

    PNG filters do not change the scanline length; validating each filter byte
    and the complete zlib stream also rejects truncated images and zip bombs.
    Both regular and Adam7-interlaced static images are supported.
    """
    if not content.startswith(PNG_SIGNATURE) or len(content) > MAX_FAVICON_BYTES:
        raise ValueError("Favicon must be a PNG of at most 1 MiB.")
    offset, header, palette, image_ended = 8, None, False, False
    image_data = bytearray()
    seen_data = False
    while offset < len(content):
        if len(content) - offset < 12:
            raise ValueError("Incomplete PNG chunk.")
        length = struct.unpack_from(">I", content, offset)[0]
        kind = content[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(content) or not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind) or kind[2] & 32:
            raise ValueError("Invalid PNG chunk.")
        data = content[offset + 8:end - 4]
        checksum = struct.unpack_from(">I", content, end - 4)[0]
        if zlib.crc32(kind + data) != checksum:
            raise ValueError("Invalid PNG checksum.")
        if header is None and kind != b"IHDR":
            raise ValueError("PNG header must be first.")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise ValueError("Invalid PNG header.")
            header = struct.unpack(">IIBBBBB", data)
            width, height, depth, color, compression, filtering, interlace = header
            if not (1 <= width <= MAX_FAVICON_DIMENSION and 1 <= height <= MAX_FAVICON_DIMENSION):
                raise ValueError("Favicon dimensions must be 1 to 512 pixels per side.")
            if depth not in COLOR_DEPTHS.get(color, ()) or compression or filtering or interlace not in {0, 1}:
                raise ValueError("Unsupported PNG encoding.")
        elif kind == b"PLTE":
            if palette or seen_data or color in {0, 4} or not length or length % 3 or length > 768 or (color == 3 and length // 3 > 2 ** depth):
                raise ValueError("Invalid PNG palette.")
            palette = True
        elif kind == b"IDAT":
            if image_ended or (color == 3 and not palette):
                raise ValueError("Invalid PNG image-data order.")
            seen_data = True
            image_data.extend(data)
        elif kind == b"IEND":
            if length or not seen_data or end != len(content):
                raise ValueError("Invalid PNG end.")
            break
        else:
            if not kind[0] & 32 or kind in {b"acTL", b"fcTL", b"fdAT"}:
                raise ValueError("Only static PNG images are supported.")
            if seen_data:
                image_ended = True
        offset = end
    else:
        raise ValueError("Missing PNG end.")

    rows = []
    passes = ADAM7 if interlace else ((0, 0, 1, 1),)
    for x, y, step_x, step_y in passes:
        columns = max(0, (width - x + step_x - 1) // step_x)
        count = max(0, (height - y + step_y - 1) // step_y)
        if columns and count:
            row_bytes = (columns * CHANNELS[color] * depth + 7) // 8
            rows.extend([row_bytes + 1] * count)
    expected = sum(rows)
    try:
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(image_data, expected + 1)
    except zlib.error as error:
        raise ValueError("Invalid PNG compressed data.") from error
    if len(decoded) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("Invalid PNG pixel-data length.")
    offset = 0
    for row_length in rows:
        if decoded[offset] > 4:
            raise ValueError("Invalid PNG scanline filter.")
        offset += row_length
    return width, height
