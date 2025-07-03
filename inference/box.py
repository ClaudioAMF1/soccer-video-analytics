# inference/box.py
class Box:
    def __init__(self, top_left, bottom_right, img):
        self.top_left = (int(top_left[0]), int(top_left[1]))
        self.bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
        self.img = self.cut(img.copy())
    def cut(self, img):
        return img[self.top_left[1]:self.bottom_right[1], self.top_left[0]:self.bottom_right[0]]