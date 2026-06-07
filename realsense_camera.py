import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pyrealsense2 as rs


class RealSenseCameraThread(threading.Thread):
    """Intel RealSense D435 컬러 스트림을 백그라운드 스레드로 받아오는 클래스.

    스레드는 파이프라인에서 계속 프레임을 읽어 최신 프레임 한 장을 락으로 보호한 채
    보관한다. 외부에서는 `get_frame()`으로 현재 프레임을 가져오거나 `capture()`로
    파일에 저장할 수 있다. Task A 실행은 이 캡처 결과(이미지 경로)를 입력으로 사용한다.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        serial: Optional[str] = None,
        warmup_frames: int = 30,
    ):
        super().__init__(daemon=True)
        self.width = width
        self.height = height
        self.fps = fps
        self.serial = serial
        self.warmup_frames = warmup_frames

        self._pipeline = rs.pipeline()
        self._config = rs.config()
        if serial:
            self._config.enable_device(serial)
        self._config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)

        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._started_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Thread lifecycle
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        self._pipeline.start(self._config)
        try:
            # 자동 노출/화이트밸런스가 안정될 때까지 초기 프레임을 버린다.
            for _ in range(self.warmup_frames):
                if self._stop_event.is_set():
                    return
                self._pipeline.wait_for_frames()

            while not self._stop_event.is_set():
                frames = self._pipeline.wait_for_frames()
                color_frame = frames.get_color_frame()
                if not color_frame:
                    continue
                image = np.asanyarray(color_frame.get_data())
                with self._lock:
                    self._frame = image
                # 첫 프레임이 실제로 저장된 뒤에 준비 완료를 알린다 (idempotent).
                self._started_event.set()
        finally:
            self._pipeline.stop()

    def stop(self) -> None:
        """스레드 루프를 멈추고 파이프라인을 정리한다."""
        self._stop_event.set()
        if self.is_alive():
            self.join(timeout=2.0)

    # ------------------------------------------------------------------ #
    # Frame access
    # ------------------------------------------------------------------ #
    def wait_until_ready(self, timeout: Optional[float] = 5.0) -> bool:
        """워밍업이 끝나고 첫 프레임이 준비될 때까지 대기한다."""
        return self._started_event.wait(timeout)

    def get_frame(self) -> Optional[np.ndarray]:
        """최신 컬러 프레임의 복사본을 반환한다 (아직 없으면 None)."""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def capture(self, save_path: str) -> Optional[str]:
        """현재 프레임을 파일로 저장하고 그 경로를 반환한다.

        프레임이 아직 준비되지 않았으면 None을 반환한다.
        """
        frame = self.get_frame()
        if frame is None:
            return None
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), frame)
        return str(path)

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #
    def __enter__(self) -> "RealSenseCameraThread":
        self.start()
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


if __name__ == "__main__":
    # 간단한 라이브 프리뷰: 'c' 키로 캡처, 'q' 키로 종료.
    cam = RealSenseCameraThread()
    cam.start()
    if not cam.wait_until_ready():
        print("카메라 준비 실패")
        cam.stop()
        raise SystemExit(1)

    print("라이브 프리뷰 시작 — [c] 캡처, [q] 종료")
    try:
        while True:
            frame = cam.get_frame()
            if frame is None:
                continue
            cv2.imshow("RealSense D435", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("c"):
                fname = f"images/capture_{int(time.time())}.png"
                saved = cam.capture(fname)
                print(f"저장됨: {saved}")
    finally:
        cam.stop()
        cv2.destroyAllWindows()
