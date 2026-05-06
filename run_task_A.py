import argparse
import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def load_prompt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run(image_path: str) -> dict:
    client = OpenAI()
    system_prompt = load_prompt("prompts/task_A.txt")

    suffix = Path(image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")
    b64 = encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="images/ 디렉토리 내 이미지 파일명 (예: sample.png)")
    args = parser.parse_args()

    result = run(f"images/{args.image}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
