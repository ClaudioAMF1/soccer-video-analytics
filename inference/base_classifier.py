# inference/base_classifier.py
from abc import ABC, abstractmethod
class BaseClassifier(ABC):
    @abstractmethod
    def predict(self, input_image): pass