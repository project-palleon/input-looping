import os
import time

import cv2
from palleon import encode_image_as_jpeg
from palleon.input_plugin import InputPlugin

# custom defined environment variables
FPS = float(os.environ["palleon_fps"])

# custom static variables
VIDEO_PATH = "test.mov"


class CamInputPlugin(InputPlugin):
    def __init__(self):
        super().__init__()

    def update_thread(self):
        cap = cv2.VideoCapture(VIDEO_PATH)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # https://stackoverflow.com/questions/33650974/opencv-python-read-specific-frame-using-videocapture
                cap.set(2, 0)
                continue

            # https://stackoverflow.com/questions/53097092/frame-from-video-is-upside-down-after-extracting
            frame = cv2.rotate(frame, cv2.ROTATE_180)

            # do the encoding without the lock to save "lock-time"
            data = encode_image_as_jpeg(frame)
            self.update_image(data)

            # wait to read the next frame
            time.sleep(1 / FPS)

    def settings_hook(self, key, value, value_type):
        print(key, value, value_type)


if __name__ == "__main__":
    CamInputPlugin().run()
