"""Condensed, chronological replay of actor actions and real oversight UI.

Screenshots are captured live into temporary storage, removed after GIF export.
The only persistent replay artifact is agent_history.gif.
"""
import base64
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


class Replay:
    def __init__(self, output: Path):
        self.output = Path(output)
        self.frames = []
        self.errors = []
        self._temporary = tempfile.TemporaryDirectory(prefix='second-look-frames-')

    async def capture(self, page, phase, detail=''):
        try:
            raw = await page.screenshot()
            folder = Path(self._temporary.name)
            path = folder / f'{len(self.frames):05d}.png'
            path.write_bytes(base64.b64decode(raw))
            self.frames.append(dict(file=str(path), phase=phase, detail=detail[:180]))
        except Exception as error:
            self.errors.append(dict(phase=phase, error=type(error).__name__))

    def finalize(self):
        try:
            self._export()
        finally:
            self._temporary.cleanup()

    def _export(self):
        if not self.frames:
            return
        images = []
        for frame in self.frames:
            with Image.open(frame['file']) as source:
                source = source.convert('RGB')
                source.thumbnail((1280, 1000))
                canvas = Image.new('RGB', (1280, 1050), 'white')
                canvas.paste(source, (0, 50))
                draw = ImageDraw.Draw(canvas)
                draw.text((12, 8), frame['phase'], fill='black')
                draw.text((12, 27), frame['detail'], fill='black')
                images.append(canvas)
        images[0].save(self.output / 'agent_history.gif', save_all=True,
            append_images=images[1:], duration=1500, loop=0, optimize=False)
