# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import onnxruntime


def softmax(vector: np.ndarray):
	e = np.exp(vector)
	return e / e.sum()


class CatOrNot:
    CAT = 0
    OTHER = 1

    INPUT_SIZE = (224, 224)
    MEAN = (0.485, 0.456, 0.406)
    STD = (0.229, 0.224, 0.225)

    def __init__(self, model_path="resnext50_32x4d.onnx"):
        self.sess = onnxruntime.InferenceSession(model_path)
    
    def predict_prob(self, image: Image.Image) -> np.ndarray:
        image = image.resize(self.INPUT_SIZE)
        arr = np.array(image).transpose((2, 0, 1)).astype(np.float32) / 255.0
        
        for i in range(3):
            arr[i] = (arr[i] - self.MEAN[i]) / self.STD[i]

        arr = np.expand_dims(arr, 0)

        input_name = self.sess.get_inputs()[0].name
        output_name = self.sess.get_outputs()[0].name
        output = self.sess.run([output_name], {input_name: arr})[0][0]

        return softmax(output)

    def predict(self, image: Image.Image) -> int:
        output = self.predict_prob(image)

        preds = np.argmax(output)

        return preds