import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from PIL import Image
from second_look.recording import Replay


class ReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_failure_is_reported_without_stopping_task(self):
        with tempfile.TemporaryDirectory() as folder:
            replay = Replay(Path(folder))
            await replay.capture(type('Page', (), {'screenshot': AsyncMock(side_effect=RuntimeError())})(), 'Actor')
            replay.finalize()
            self.assertEqual(replay.errors[0]['error'], 'RuntimeError')
            self.assertFalse(replay.frames)
            self.assertEqual(list(Path(folder).iterdir()), [])

    async def test_chronology_and_gif_export(self):
        with tempfile.TemporaryDirectory() as folder:
            replay = Replay(Path(folder))
            for phase, color in [('Actor proposal', 'white'), ('Second Look', 'blue'), ('User response: adjust', 'green')]:
                data = io.BytesIO()
                Image.new('RGB', (100, 100), color).save(data, format='PNG')
                page = type('Page', (), {'screenshot': AsyncMock(return_value=base64.b64encode(data.getvalue()).decode())})()
                await replay.capture(page, phase)
            replay.finalize()
            self.assertEqual(replay.frames[-1]['phase'], 'User response: adjust')
            self.assertEqual([p.name for p in Path(folder).iterdir()], ['agent_history.gif'])
            self.assertFalse(Path(replay.frames[0]['file']).exists())
            with Image.open(Path(folder)/'agent_history.gif') as gif:
                self.assertEqual(gif.n_frames, 3)
