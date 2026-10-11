#!/usr/bin/env python3
"""Render a short cinematic Levantine mate-gathering film."""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import arabic_reshaper
import imageio_ffmpeg
import numpy as np
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "media"
OUTPUT = ROOT / "mate_on_your_terms.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 24
DURATION = 34.4
BASE_WIDTH, BASE_HEIGHT = 2208, 1242
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"
FONT_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
if not FONT_REGULAR.exists():
    FONT_REGULAR = Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf")
if not FONT_BOLD.exists():
    FONT_BOLD = Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")

IMAGES = {
    "wide": MEDIA / "mate_wide.png",
    "kettles": MEDIA / "mate_kettles.png",
    "cup": MEDIA / "mate_expressions.png",
}

# Speech timings (seconds) are also used for the subtitles and cup-mouth animation.
FEMALE_START = 2.35
MALE_START = 12.55
CUP_START = 28.35
CUP_END = CUP_START + 1.56

# The base images are overscanned, so a small crop movement gives each still gentle camera motion.
MOTION = {
    "wide": (20, 195, 42, 88),
    "kettles": (52, 127, 58, 104),
    "cup": (26, 112, 55, 91),
    "outro": (85, 175, 63, 82),
}


def ar(text: str) -> str:
    """Shape Arabic and reorder it for Pillow's non-RAQM text renderer."""
    return get_display(arabic_reshaper.reshape(text))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def prepare_images() -> dict[str, Image.Image]:
    prepared: dict[str, Image.Image] = {}
    for key, path in IMAGES.items():
        image = Image.open(path).convert("RGB")
        image = ImageOps.fit(image, (BASE_WIDTH, BASE_HEIGHT), method=Image.Resampling.LANCZOS)
        image = ImageEnhance.Color(image).enhance(1.035)
        image = ImageEnhance.Contrast(image).enhance(1.035)
        warm = Image.new("RGB", image.size, (245, 176, 104))
        image = Image.blend(image, warm, 0.025)
        prepared[key] = image
    prepared["outro"] = prepared["wide"]
    return prepared


def scene_frame(images: dict[str, Image.Image], scene: str, progress: float, t: float) -> Image.Image:
    x0, x1, y0, y1 = MOTION[scene]
    p = ease(progress)
    crop_x = int(x0 + (x1 - x0) * p)
    crop_y = int(y0 + (y1 - y0) * p)
    source_key = "wide" if scene == "outro" else scene
    frame = images[source_key].crop((crop_x, crop_y, crop_x + WIDTH, crop_y + HEIGHT))

    if scene == "kettles":
        fade = min(1.0, max(0.0, (t - 12.02) / 0.45), max(0.0, (27.15 - t) / 0.45))
        if fade > 0:
            frame = add_kettle_labels(frame, fade, crop_x)
    elif scene == "cup":
        frame = add_talking_cup(frame, t, crop_x, crop_y)
    return frame


def add_kettle_labels(frame: Image.Image, alpha: float, crop_x: int) -> Image.Image:
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Source-image kettle centres are translated with the same slow camera pan as the shot.
    scale_x = BASE_WIDTH / 1376.0
    gauges = [
        (390, "تغلي", "١٠٠°م", 100, (243, 91, 58, 255)),
        (700, "وسط", "٨٠°م", 80, (241, 166, 63, 255)),
        (1020, "دافية", "٦٠°م", 60, (86, 191, 163, 255)),
    ]
    for source_x, label, temperature, degrees, color in gauges:
        center_x = int(source_x * scale_x) - crop_x
        label_box = (center_x - 118, 178, center_x + 118, 248)
        draw.rounded_rectangle(label_box, radius=28, fill=(15, 20, 19, 195), outline=(226, 192, 126, 240), width=2)
        draw.text((center_x, 213), ar(label), font=font(31, True), fill=(255, 242, 215, 255), anchor="mm")

        # A compact digital thermometer panel sits on each kettle body, with a matching liquid gauge.
        panel = (center_x - 124, 572, center_x + 124, 716)
        draw.rounded_rectangle(panel, radius=24, fill=(8, 15, 16, 218), outline=(240, 222, 184, 230), width=2)
        draw.text((center_x + 23, 597), ar("حرارة المي"), font=font(20, True), fill=(244, 225, 190, 255), anchor="mm")
        draw.text((center_x + 24, 658), ar(temperature), font=font(38, True), fill=(255, 252, 242, 255), anchor="mm")

        gauge_x = center_x - 78
        tube = (gauge_x - 9, 603, gauge_x + 9, 658)
        draw.rounded_rectangle(tube, radius=10, fill=(17, 23, 23, 245), outline=(255, 247, 230, 250), width=2)
        liquid_top = 651 - int(34 * degrees / 100)
        draw.rounded_rectangle((gauge_x - 4, liquid_top, gauge_x + 4, 652), radius=4, fill=color)
        draw.ellipse((gauge_x - 15, 644, gauge_x + 15, 674), fill=color, outline=(255, 247, 230, 250), width=2)

    layer.putalpha(layer.getchannel("A").point(lambda value: int(value * alpha)))
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def add_talking_cup(frame: Image.Image, t: float, crop_x: int, crop_y: int) -> Image.Image:
    # The still already shows three expressive glasses; gently animate the open mouth
    # of the puzzled centre glass only while its one-line question is spoken.
    if not (CUP_START - 0.12 <= t <= CUP_END + 0.14):
        return frame
    scale_x = BASE_WIDTH / 1376.0
    scale_y = BASE_HEIGHT / 768.0
    cx = int(0.501 * BASE_WIDTH) - crop_x
    mouth_y = int(0.635 * BASE_HEIGHT) - crop_y
    if not (0 <= cx < WIDTH and 0 <= mouth_y < HEIGHT):
        return frame

    syllable = abs(math.sin((t - CUP_START) * 11.5))
    mouth_h = int((5 + 9 * (0.22 + 0.78 * syllable)) * scale_y)
    mouth_w = int(20 * scale_x)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((cx - mouth_w // 2, mouth_y - mouth_h // 2, cx + mouth_w // 2, mouth_y + mouth_h // 2),
                 fill=(24, 33, 26, 232), outline=(228, 197, 143, 180), width=2)
    if mouth_h > 17:
        inner_h = max(3, mouth_h // 4)
        draw.ellipse((cx - mouth_w // 4, mouth_y - inner_h // 2, cx + mouth_w // 4, mouth_y + inner_h // 2),
                     fill=(137, 73, 63, 210))
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def text_width(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), ar(text), font=use_font)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and text_width(draw, candidate, use_font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def fade_layer(layer: Image.Image, alpha: float) -> Image.Image:
    alpha = max(0.0, min(1.0, alpha))
    if alpha >= 0.999:
        return layer
    layer.putalpha(layer.getchannel("A").point(lambda value: int(value * alpha)))
    return layer


def title_overlay(frame: Image.Image, t: float) -> Image.Image:
    if t < 0.28 or t > 3.0:
        return frame
    alpha = min(1.0, (t - 0.28) / 0.45, (3.0 - t) / 0.48)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((435, 72, 1485, 326), radius=38, fill=(9, 14, 13, 125), outline=(224, 186, 113, 100), width=2)
    draw.text((960, 157), ar("متّة على المزاج"), font=font(78, True), fill=(255, 235, 193, 255), anchor="mm",
              stroke_width=2, stroke_fill=(36, 21, 9, 210))
    draw.rounded_rectangle((833, 218, 1087, 223), radius=3, fill=(226, 185, 108, 240))
    draw.text((960, 274), ar("ثلاث إباريق... وثلاث أذواق"), font=font(36, False), fill=(255, 248, 229, 255), anchor="mm")
    return Image.alpha_composite(frame.convert("RGBA"), fade_layer(layer, alpha)).convert("RGB")


SUBTITLES = [
    (2.35, 5.65, "صديقة من القعدة", "يلا يا جماعة، كلّ واحد بدّه المي على مزاجه!"),
    (5.65, 9.20, "صديقة من القعدة", "أبو سامر بدّه ياها تغلي، وأم جاد بدها بس دافية"),
    (9.20, 12.55, "صديقة من القعدة", "وأنا بدي ياها بالنص."),
    (12.55, 15.80, "أبو سامر", "أنا بحبّ المي تكون حامية كتير."),
    (15.80, 19.25, "أبو سامر", "بس خيي بدّه ياها دافية، وبنتي بتحبها بالنص."),
    (19.25, 23.05, "أبو سامر", "مشان هيك عنا تلات إباريق عالغاز؛ واحد لكل مزاج."),
    (23.05, 27.40, "أبو سامر", "المهم تبقى المتّة سخنة والقعدة حلوة!"),
]


def subtitle_overlay(frame: Image.Image, t: float) -> Image.Image:
    cue = next((item for item in SUBTITLES if item[0] <= t < item[1]), None)
    if cue is None:
        return frame
    start, end, speaker, caption = cue
    alpha = min(1.0, (t - start) / 0.20, (end - t) / 0.20)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((110, 817, 1810, 1012), radius=32, fill=(8, 13, 13, 197), outline=(226, 188, 118, 135), width=2)
    draw.rounded_rectangle((1668, 841, 1744, 847), radius=3, fill=(229, 189, 115, 250))
    draw.text((1758, 837), ar(speaker), font=font(27, True), fill=(237, 205, 147, 255), anchor="ra")
    sub_font = font(42, True)
    lines = wrap_text(draw, caption, sub_font, 1550)
    if len(lines) == 1:
        draw.text((1750, 925), ar(lines[0]), font=sub_font, fill=(255, 250, 239, 255), anchor="rm",
                  stroke_width=1, stroke_fill=(13, 14, 12, 190))
    else:
        line_font = font(37, True)
        for index, line in enumerate(lines[:2]):
            draw.text((1750, 894 + index * 48), ar(line), font=line_font, fill=(255, 250, 239, 255), anchor="rm",
                      stroke_width=1, stroke_fill=(13, 14, 12, 190))
    return Image.alpha_composite(frame.convert("RGBA"), fade_layer(layer, alpha)).convert("RGB")


def cup_speech_bubble(frame: Image.Image, t: float) -> Image.Image:
    if t < 28.20 or t > 31.15:
        return frame
    alpha = min(1.0, (t - 28.20) / 0.22, (31.15 - t) / 0.35)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # The tail points toward the three expressive mate glasses; only the requested question is spoken.
    draw.polygon([(1160, 231), (1265, 231), (1035, 535)], fill=(250, 244, 225, 246), outline=(224, 187, 116, 245))
    draw.rounded_rectangle((1080, 55, 1810, 250), radius=40, fill=(250, 244, 225, 246), outline=(224, 187, 116, 255), width=4)
    draw.text((1445, 128), ar("انتو كيف بتحبوني؟"), font=font(52, True), fill=(37, 50, 35, 255), anchor="mm")
    draw.text((1748, 212), ar("كاسات المتّة"), font=font(23, True), fill=(122, 93, 49, 255), anchor="ra")
    return Image.alpha_composite(frame.convert("RGBA"), fade_layer(layer, alpha)).convert("RGB")


def outro_overlay(frame: Image.Image, t: float) -> Image.Image:
    if t < 31.12:
        return frame
    alpha = min(1.0, (t - 31.12) / 0.36, (DURATION - t) / 0.5)
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((420, 330, 1500, 650), radius=44, fill=(8, 15, 13, 174), outline=(226, 188, 118, 170), width=2)
    draw.text((960, 438), ar("انتو كيف بتحبوني؟"), font=font(74, True), fill=(255, 234, 187, 255), anchor="mm",
              stroke_width=2, stroke_fill=(39, 23, 10, 220))
    draw.rounded_rectangle((803, 508, 1117, 514), radius=3, fill=(228, 190, 121, 240))
    draw.text((960, 573), ar("كلّ واحد وإله مزاجه"), font=font(38, False), fill=(255, 248, 228, 255), anchor="mm")
    return Image.alpha_composite(frame.convert("RGBA"), fade_layer(layer, alpha)).convert("RGB")


def make_frame(images: dict[str, Image.Image], t: float) -> Image.Image:
    if t < 11.90:
        frame = scene_frame(images, "wide", t / 12.55, t)
    elif t < 12.55:
        amount = ease((t - 11.90) / 0.65)
        left = scene_frame(images, "wide", t / 12.55, t)
        right = scene_frame(images, "kettles", (t - 11.90) / 15.40, t)
        frame = Image.blend(left, right, amount)
    elif t < 26.75:
        frame = scene_frame(images, "kettles", (t - 11.90) / 15.40, t)
    elif t < 27.45:
        amount = ease((t - 26.75) / 0.70)
        left = scene_frame(images, "kettles", (t - 11.90) / 15.40, t)
        right = scene_frame(images, "cup", (t - 26.75) / 4.00, t)
        frame = Image.blend(left, right, amount)
    elif t < 30.80:
        frame = scene_frame(images, "cup", (t - 26.75) / 4.00, t)
    elif t < 31.50:
        amount = ease((t - 30.80) / 0.70)
        left = scene_frame(images, "cup", (t - 26.75) / 4.00, t)
        right = scene_frame(images, "outro", (t - 30.80) / 3.60, t)
        frame = Image.blend(left, right, amount)
    else:
        frame = scene_frame(images, "outro", (t - 30.80) / 3.60, t)

    frame = title_overlay(frame, t)
    frame = subtitle_overlay(frame, t)
    frame = cup_speech_bubble(frame, t)
    frame = outro_overlay(frame, t)

    # A restrained opening/closing fade adds a finished film-like landing.
    fade_in = max(0.0, min(1.0, t / 0.75))
    fade_out = max(0.0, min(1.0, (DURATION - t) / 0.68))
    fade = min(fade_in, fade_out)
    if fade < 0.999:
        frame = Image.blend(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)), frame, fade)
    return frame


def make_ambient_wav(path: Path) -> None:
    """Create a very quiet warm instrumental bed; it stays well under the dialogue."""
    sample_rate = 48_000
    sample_count = int(sample_rate * DURATION)
    audio = np.zeros(sample_count, dtype=np.float32)
    chord_sets = [
        (146.83, 220.00, 293.66),
        (130.81, 196.00, 261.63),
        (110.00, 164.81, 220.00),
        (123.47, 185.00, 246.94),
    ]
    segment_seconds = 6.0
    for start in np.arange(0.0, DURATION, segment_seconds):
        begin = int(start * sample_rate)
        finish = min(sample_count, int((start + segment_seconds) * sample_rate))
        local = np.arange(finish - begin, dtype=np.float32) / sample_rate
        env = np.clip(local / 0.75, 0, 1) * np.clip((segment_seconds - local) / 1.0, 0, 1)
        chord = chord_sets[int(start // segment_seconds) % len(chord_sets)]
        layer = np.zeros_like(local)
        for i, frequency in enumerate(chord):
            layer += (0.62 / (i + 1)) * np.sin(2 * np.pi * frequency * local + 0.24 * i)
            layer += 0.12 * np.sin(2 * np.pi * frequency * 2.0 * local + 0.18 * i)
        audio[begin:finish] += layer * env * 0.030

    # Sparse, soft plucks suggest a mellow Levantine-inspired underscore without competing with speech.
    notes = [220.00, 261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 440.00]
    beat = 0.86
    note_time = 0.25
    note_index = 0
    while note_time < DURATION - 0.25:
        begin = int(note_time * sample_rate)
        length = min(int(0.48 * sample_rate), sample_count - begin)
        local = np.arange(length, dtype=np.float32) / sample_rate
        frequency = notes[note_index % len(notes)]
        envelope = np.exp(-9.5 * local) * np.clip(local / 0.025, 0, 1)
        pluck = np.sin(2 * np.pi * frequency * local) + 0.22 * np.sin(2 * np.pi * frequency * 2.0 * local)
        audio[begin:begin + length] += pluck * envelope * 0.018
        note_time += beat
        note_index += 1

    audio = np.clip(audio, -0.11, 0.11)
    stereo = np.column_stack((audio, audio))
    pcm = (stereo * 32767).astype("<i2")
    with wave.open(str(path), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(sample_rate)
        file.writeframes(pcm.tobytes())


def run() -> None:
    MEDIA.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    images = prepare_images()
    frames_total = int(round(DURATION * FPS))

    with tempfile.TemporaryDirectory(prefix="mate-film-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        silent_path = temp_dir_path / "picture.mp4"
        ambient_path = temp_dir_path / "ambient.wav"
        make_ambient_wav(ambient_path)

        command = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(silent_path),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert process.stdin is not None
        try:
            for frame_number in range(frames_total):
                t = frame_number / FPS
                frame = make_frame(images, t)
                process.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
                if frame_number % (FPS * 5) == 0:
                    print(f"Rendering {t:05.1f}s / {DURATION:.1f}s", file=sys.stderr, flush=True)
        finally:
            process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("FFmpeg failed while encoding the video frames")

        mix_filter = (
            "[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay=2350|2350,volume=1.08[female];"
            "[2:a]aresample=48000,aformat=channel_layouts=stereo,adelay=12550|12550,volume=1.08[male];"
            "[3:a]aresample=48000,aformat=channel_layouts=stereo,adelay=28350|28350,"
            "aecho=0.8:0.22:82:0.13,volume=1.08[cup];"
            "[4:a]volume=0.34,afade=t=in:st=0:d=1.8,afade=t=out:st=31:d=3[bed];"
            "[female][male][cup][bed]amix=inputs=4:duration=longest:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.94,atrim=duration=34.4[mix]"
        )
        mux_command = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(silent_path),
            "-i", str(MEDIA / "voice_female_intro.mp3"),
            "-i", str(MEDIA / "voice_male_reply.mp3"),
            "-i", str(MEDIA / "voice_cup.mp3"),
            "-i", str(ambient_path),
            "-filter_complex", mix_filter,
            "-map", "0:v:0", "-map", "[mix]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{DURATION:.2f}", "-movflags", "+faststart", str(OUTPUT),
        ]
        subprocess.run(mux_command, check=True)

    print(f"Created: {OUTPUT}")
    print(f"Resolution: {WIDTH}x{HEIGHT} at {FPS} fps, {DURATION:.1f} seconds")


if __name__ == "__main__":
    run()
