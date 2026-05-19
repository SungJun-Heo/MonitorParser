import argparse
import json

from taskAParser import taskAParser

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="images/ 디렉토리 내 이미지 파일명 (예: task_A_1.png)")
    parser.add_argument("--evaluate", action="store_true", help="images/ 내 모든 이미지 평가")
    args = parser.parse_args()

    task_parser = taskAParser()

    if args.evaluate:
        task_parser.evaluate()
    elif args.image:
        result = task_parser.run(f"images/{args.image}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
