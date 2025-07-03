# inference/detector.py
from typing import List
import pandas as pd
from ultralytics import YOLO
from .base_detector import BaseDetector
import numpy as np 
class Detector(BaseDetector):
    def __init__(self, model_path: str = "yolov8x.pt"):
        try:
            self.model = YOLO(model_path)
            self.device = self.model.device
        except Exception as e:
            raise e

    def predict(self, input_image: List[np.ndarray]) -> pd.DataFrame:
        results = self.model(input_image, verbose=False)
        all_preds_df = []
        for result in results:
            if result.boxes:
                preds_df = pd.DataFrame(result.boxes.data.cpu().numpy(), columns=['xmin', 'ymin', 'xmax', 'ymax', 'confidence', 'class'])
                names = result.names
                preds_df['name'] = preds_df['class'].apply(lambda x: names[int(x)])
                all_preds_df.append(preds_df)
        if not all_preds_df: return pd.DataFrame()
        return pd.concat(all_preds_df, ignore_index=True)