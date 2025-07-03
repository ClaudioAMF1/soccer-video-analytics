# inference/base_detector.py
from abc import ABC, abstractmethod
import pandas as pd
class BaseDetector(ABC):
    @abstractmethod
    def predict(self, input_image): pass