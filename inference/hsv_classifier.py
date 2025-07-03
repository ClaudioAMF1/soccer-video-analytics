# inference/hsv_classifier.py
import cv2
import numpy as np
import copy
from .base_classifier import BaseClassifier
class HSVClassifier(BaseClassifier):
    def __init__(self, filters):
        self.filters = filters
    def predict(self, input_images):
        return [self._predict_img(img) for img in input_images]
    def _predict_img(self, img):
        if img is None or img.size == 0: return "unknown"
        max_pixels = -1
        predicted_team = "unknown"
        for team_filter in self.filters:
            pixel_count = 0
            for color in team_filter["colors"]:
                pixel_count += self._count_color_pixels(img, color)
            if pixel_count > max_pixels:
                max_pixels = pixel_count
                predicted_team = team_filter["name"]
        return predicted_team
    def _count_color_pixels(self, img, color_filter):
        img_hsv = cv2.cvtColor(self._crop_jersey(img), cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(img_hsv, color_filter["lower_hsv"], color_filter["upper_hsv"])
        return cv2.countNonZero(mask)
    def _crop_jersey(self, img):
        h, w, _ = img.shape
        return img[int(h * 0.15):int(h * 0.6), int(w * 0.1):int(w * 0.9)]