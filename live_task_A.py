import argparse
import json
import threading
import time
from pathlib import Path

import cv2

from realsense_camera import RealSenseCameraThread
from taskAParser import taskAParser

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
CAPTURE_DIR = IMAGES_DIR / "captures"


def run_task_a(parser: taskAParser, image_path: str) -> None:
    """캡처한 이미지로 Task A를 실행하고 결과를 출력한다 (백그라운드 스레드용)."""
    print(f"\n[Task A] 실행 중... ({image_path})")
    try:
        result = parser.run(image_path)
        print("[Task A] 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[Task A] 실패: {e}")


def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="RealSense D435 라이브 스트림에서 'c' 키로 프레임을 캡처해 Task A 실행"
    )
    arg_parser.add_argument(
        "--prompt", default="task_A_with_text.txt",
        help="prompts/ 디렉토리 내 프롬프트 파일명",
    )
    arg_parser.add_argument("--width", type=int, default=640)
    arg_parser.add_argument("--height", type=int, default=480)
    arg_parser.add_argument("--fps", type=int, default=30)
    arg_parser.add_argument(
        "--serial", default="138422073714",
        help="RealSense 장치 시리얼 번호 (여러 대 연결 시 선택)",
    )
    args = arg_parser.parse_args()

    prompt_path = BASE_DIR / "prompts" / args.prompt
    if not prompt_path.exists():
        raise SystemExit(f"프롬프트 파일이 없습니다: {prompt_path}")

    task_parser = taskAParser(prompt_path=str(prompt_path))

    cam = RealSenseCameraThread(
        width=args.width, height=args.height, fps=args.fps, serial=args.serial
    )
    cam.start()
    if not cam.wait_until_ready():
        print("카메라 준비 실패")
        cam.stop()
        raise SystemExit(1)

    print("라이브 프리뷰 시작 — [c] 캡처 후 Task A 실행, [q] 종료")
    try:
        while True:
            frame = cam.get_frame()
            if frame is None:
                continue
            cv2.imshow("RealSense D435 — [c] capture / [q] quit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                save_path = CAPTURE_DIR / f"capture_{int(time.time())}.png"
                saved = cam.capture(str(save_path))
                if saved is None:
                    print("프레임이 아직 준비되지 않았습니다.")
                    continue
                print(f"\n저장됨: {saved}")
                # Task A는 수 초 걸리므로 별도 스레드에서 실행 (프리뷰 끊김 방지)
                threading.Thread(
                    target=run_task_a, args=(task_parser, saved), daemon=True
                ).start()
    finally:
        cam.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
