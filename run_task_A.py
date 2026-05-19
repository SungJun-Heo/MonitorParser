import argparse
import json

from taskAParser import taskAParser

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="prompts/ 디렉토리 내 프롬프트 파일명 (예: task_A_with_text.txt)")
    parser.add_argument("--image", required=True, help="images/ 디렉토리 내 이미지 파일명 (예: task_A_1.png)")
    args = parser.parse_args()

    task_parser = taskAParser(prompt_path=f"prompts/{args.prompt}")
    result = task_parser.run(f"images/{args.image}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
