import cv2
import numpy as np


def load_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(
            f"Could not read image: {image_path}"
        )

    return image


def resize_image(image, width=1600):
    h, w = image.shape[:2]

    if w <= width:
        return image

    ratio = width / float(w)
    new_height = int(h * ratio)

    return cv2.resize(
        image,
        (width, new_height),
        interpolation=cv2.INTER_AREA
    )


def enhance_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    enhanced = cv2.equalizeHist(denoised)

    return enhanced


def preprocess_image(image_path):
    image = load_image(image_path)

    image = resize_image(image)

    processed = enhance_image(image)

    return processed


def save_preprocessed(image_path, output_path):
    processed = preprocess_image(image_path)

    cv2.imwrite(output_path, processed)

    return output_path


