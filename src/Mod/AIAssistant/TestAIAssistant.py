# SPDX-License-Identifier: LGPL-2.1-or-later

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from AIAssistantCore import build_messages, extract_code_block, parse_sse_data_line


class TestAIAssistant(unittest.TestCase):
    def test_extract_python_fence(self):
        text = """Some intro\n```python\nimport FreeCAD as App\nprint('ok')\n```\nnotes"""
        code = extract_code_block(text)
        self.assertEqual(code, "import FreeCAD as App\nprint('ok')")

    def test_extract_plain_text_when_no_fence(self):
        text = "App.newDocument('Doc')"
        code = extract_code_block(text)
        self.assertEqual(code, text)

    def test_parse_sse_token(self):
        line = 'data: {"choices":[{"delta":{"content":"abc"}}]}'
        kind, value = parse_sse_data_line(line)
        self.assertEqual(kind, "token")
        self.assertEqual(value, "abc")

    def test_parse_sse_done(self):
        kind, value = parse_sse_data_line("data: [DONE]")
        self.assertEqual(kind, "done")
        self.assertIsNone(value)

    def test_build_messages(self):
        messages = build_messages("Create a cube", "Doc")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
