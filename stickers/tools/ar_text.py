#!/usr/bin/env python3
"""
عارض نصوص عربية عالي الجودة بدون HarfBuzz مدمج في Pillow:
تشكيل عبر uharfbuzz + رسم المحارف عبر FreeType.

    from ar_text import ArabicText
    t = ArabicText("fonts/Cairo-ExtraBold.ttf")
    img, size = t.render("كونوا مع هيا", 64, fill=(74, 32, 61))
"""
import uharfbuzz as hb
import freetype


class ArabicText:
    def __init__(self, path):
        self.path = path
        blob = hb.Blob.from_file_path(path)
        self.hb_face = hb.Face(blob)
        self.hb_font = hb.Font(self.hb_face)
        self.upem = self.hb_face.upem
        self.ft = freetype.Face(path)

    # ---------- shaping ----------
    def _shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        if buf.direction is None:
            buf.direction = "rtl"
        if buf.script is None:
            buf.script = "Arab"
        hb.shape(self.hb_font, buf)
        return buf.glyph_infos, buf.glyph_positions

    def advance(self, text, size):
        infos, poss = self._shape(text)
        s = size / self.upem
        return sum(p.x_advance for p in poss) * s

    def measure_width(self, text, size):
        return self.advance(text, size)

    # ---------- rendering ----------
    def render(self, text, size, fill=(0, 0, 0, 255), baseline=None):
        """يرجع (صورة RGBA مقصوصة على الحبر، (العرض الكلي، الارتفاع الكلي))"""
        from PIL import Image, ImageDraw

        infos, poss = self._shape(text)
        s = size / self.upem
        pad = max(4, int(size * 0.06))
        total_adv = sum(p.x_advance for p in poss) * s

        # حساب الصندوق
        self.ft.set_char_size(int(size * 64))
        xs, ys = [], []
        pen = 0.0
        for info, pos in zip(infos, poss):
            self.ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            g = self.ft.glyph
            bm = g.bitmap
            left = pen + (pos.x_offset * s) + g.bitmap_left
            top = -(pos.y_offset * s) - g.bitmap_top
            xs.extend([left, left + bm.width])
            ys.extend([top, top + bm.rows])
            pen += pos.x_advance * s
        if not xs:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), (0, 0)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        W = int(max(total_adv, max_x) - min(min_x, 0)) + pad * 2
        H = int(max_y - min_y) + pad * 2

        mask = Image.new("L", (W, H), 0)
        pen = 0.0
        for info, pos in zip(infos, poss):
            self.ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            g = self.ft.glyph
            bm = g.bitmap
            if bm.width and bm.rows:
                buf = bm.buffer
                pitch = bm.pitch
                if pitch < 0:
                    rows = [buf[i * -pitch:(i * -pitch) + bm.width] for i in range(bm.rows)]
                    rows.reverse()
                    data = b"".join(rows)
                    pitch = bm.width
                else:
                    data = bytes(buf)[:pitch * bm.rows]
                gl = Image.frombytes("L", (bm.width, bm.rows), data)
                if pitch != bm.width:
                    gl = Image.frombytes("L", (bm.width, bm.rows),
                                         b"".join(data[i * pitch:i * pitch + bm.width]
                                                  for i in range(bm.rows)))
                x = int(round(pen + pos.x_offset * s + g.bitmap_left - min(min_x, 0) + pad))
                y = int(round(-pos.y_offset * s - g.bitmap_top - min_y + pad))
                mask.paste(gl, (x, y), gl)
            pen += pos.x_advance * s

        img = Image.new("RGBA", (W, H), fill)
        img.putalpha(mask)
        bbox = mask.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img, (int(total_adv), int(max_y - min_y))

    def fit(self, text, max_size, max_width, min_size=16):
        for size in range(int(max_size), int(min_size) - 1, -1):
            if self.advance(text, size) <= max_width:
                return size
        return int(min_size)
