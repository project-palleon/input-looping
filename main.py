import io
import os
import struct
import time
from threading import Thread, Lock
from typing import Optional

import cv2

from simple_socket import SimpleSocket

# env variables that are always passed to the program
HOST = os.environ["PALLEON_HOST"]
PORT = int(os.environ["PALLEON_PORT"])

# custom defined environment variables
FPS = float(os.environ["palleon_fps"])

# custom static variables
VIDEO_PATH = "test.mov"

# state tracking variables and so on to make this function work
# I think they have self-explanatory names
current_image: Optional[bytes] = None
current_image_lock = Lock()
current_image_already_sent = False
current_image_already_sent_lock = Lock()


def encode_image_as_jpeg(frame):
    # saving bandwidth, i.e. traiding cpu vs network/storage
    _, buf = cv2.imencode(".jpeg", frame)
    buffer = io.BytesIO(buf)
    return buffer.getvalue()


def image_collector():
    global current_image, current_image_lock, current_image_already_sent, current_image_already_sent_lock

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
        with current_image_lock:
            current_image = data
            with current_image_already_sent_lock:
                current_image_already_sent = False

        # wait to read the next frame
        time.sleep(1 / FPS)


def core_connector():
    global current_image_already_sent

    with SimpleSocket(HOST, PORT) as s:
        while True:
            instruction = s.recv_exactly(1)

            match instruction:
                case b"s":
                    # mvp of a method the input plugin could receive settings from the core
                    length_key, length_value, value_type = struct.unpack("<iii", s.recv_exactly(3 * 4))
                    key_and_value = s.recv_exactly(length_key + length_value)
                    key = key_and_value[:length_key]
                    value = key_and_value[length_key: length_key + length_value]
                    print(key, value, value_type)
                case b"i":
                    # the server requested an image
                    # it was a deliberate decision so the server could decide when to handle new input
                    # because otherwise it could lead to a DOS like situation
                    with current_image_already_sent_lock:
                        if current_image_already_sent:
                            # no new image was loaded
                            s.sendall(struct.pack("<i", 2))
                        else:
                            with current_image_lock:
                                if current_image:
                                    data = struct.pack("<i", 1) + struct.pack("<i", len(current_image)) + current_image
                                    s.sendall(data)
                                    current_image_already_sent = True
                                else:
                                    # no data atm
                                    # in principle the same as 2 (nop) but it implies "it could take
                                    # longer, so please wait some time before further requests"
                                    s.sendall(struct.pack("<i", 0))


def main():
    # 1) collect new data in thread #1
    # 2) wait for the server to ask for new images in #2

    collector = Thread(target=image_collector)
    collector.daemon = True
    connector = Thread(target=core_connector)
    connector.daemon = True
    collector.start()
    connector.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
