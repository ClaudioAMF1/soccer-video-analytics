# inference/converter.py
import norfair
import numpy as np
import pandas as pd
class Converter:
    @staticmethod
    def DataFrame_to_Detections(df: pd.DataFrame):
        detections = []
        for _, row in df.iterrows():
            box = np.array([[row["xmin"], row["ymin"]], [row["xmax"], row["ymax"]]])
            data = {"name": row["name"], "p": row.get("confidence", 0)}
            detections.append(norfair.Detection(points=box, data=data))
        return detections
    @staticmethod
    def TrackedObjects_to_Detections(tracked_objects):
        detections = []
        for obj in tracked_objects:
            if obj.live_points.any():
                detection = obj.last_detection
                detection.data["id"] = int(obj.id)
                detections.append(detection)
        return detections