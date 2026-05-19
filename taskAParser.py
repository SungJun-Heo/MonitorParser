import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class taskAParser:
    def __init__(self, prompt_path: str):
        self.client = OpenAI()
        self.system_prompt = self._load_prompt(prompt_path)

    @staticmethod
    def _load_prompt(path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def run(self, image_path: str) -> dict:
        suffix = Path(image_path).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/jpeg")
        b64 = self._encode_image(image_path)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

