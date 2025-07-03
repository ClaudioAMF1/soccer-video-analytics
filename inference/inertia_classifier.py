# inference/inertia_classifier.py
class InertiaClassifier:
    def __init__(self, classifier, inertia=25):
        self.classifier = classifier
        self.inertia = inertia
        self.classifications_per_id = {}
    def predict_from_detections(self, detections, img):
        if not detections: return []
        imgs_to_classify = [self._get_img_from_detection(det, img) for det in detections]
        predictions = self.classifier.predict(imgs_to_classify)
        for det, pred in zip(detections, predictions):
            det_id = det.data.get("id")
            if det_id not in self.classifications_per_id:
                self.classifications_per_id[det_id] = []
            self.classifications_per_id[det_id].append(pred)
            if len(self.classifications_per_id[det_id]) > self.inertia:
                self.classifications_per_id[det_id].pop(0)
            det.data["classification"] = max(set(self.classifications_per_id[det_id]), key=self.classifications_per_id[det_id].count)
        return detections
    def _get_img_from_detection(self, det, img):
        p1, p2 = det.points.astype(int)
        return img[p1[1]:p2[1], p1[0]:p2[0]]