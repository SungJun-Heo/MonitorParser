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


def normalize_parts(parts: list) -> dict:
    return {p["name"]: p["quantity"] for p in parts if p["quantity"] > 0}


def compare(actual: dict, expected: dict) -> list[str]:
    errors = []
    if normalize_parts(actual.get("target_parts", [])) != normalize_parts(expected.get("target_parts", [])):
        errors.append(f"  target_parts: 실제={actual.get('target_parts')} / 기대={expected.get('target_parts')}")
    if actual.get("total_count") != expected.get("total_count"):
        errors.append(f"  total_count: 실제={actual.get('total_count')} / 기대={expected.get('total_count')}")
    return errors


def evaluate():
    with open("ground_truth.json", encoding="utf-8") as f:
        ground_truth = json.load(f)

    images = sorted(Path("images").glob("*.png"))
    results = {"pass": 0, "fail": 0}

    for image_path in images:
        name = image_path.stem
        print(f"\n[{name}]")

        if name not in ground_truth:
            print(f"  건너뜀: ground_truth.json에 항목 없음")
            continue

        try:
            actual = run(str(image_path))
            print(f"  출력: {json.dumps(actual, ensure_ascii=False)}")
        except Exception as e:
            print(f"  API 오류: {e}")
            results["fail"] += 1
            continue

        diffs = compare(actual, ground_truth[name])
        if diffs:
            print("  결과: FAIL")
            for d in diffs:
                print(d)
            results["fail"] += 1
        else:
            print("  결과: PASS")
            results["pass"] += 1

    total = results["pass"] + results["fail"]
    print(f"\n{'='*40}")
    print(f"결과: {results['pass']}/{total} PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="images/ 디렉토리 내 이미지 파일명 (예: task_A_1.png)")
    parser.add_argument("--evaluate", action="store_true", help="images/ 내 모든 이미지 평가")
    args = parser.parse_args()

    if args.evaluate:
        evaluate()
    elif args.image:
        result = run(f"images/{args.image}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
