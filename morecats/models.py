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


class NeuralHash:
    def __init__(
        self,
        model_path="neuralhash.onnx",
        seed_path="neuralhash_128x96_seed1.dat"
    ):
        self.sess = onnxruntime.InferenceSession(model_path)
        with open(seed_path, 'rb') as file:
            self.seed = np.frombuffer(file.read()[128:], dtype=np.float32)
        self.seed = self.seed.reshape([96, 128])
    
    def calc_bits(self, image: Image.Image) -> np.ndarray:
        image = image.resize((360, 360))
        arr = np.array(image).astype(np.float32) / 255.0
        arr = arr * 2.0 - 1.0
        arr = arr.transpose(2, 0, 1).reshape([1, 3, 360, 360])

        inputs = {self.sess.get_inputs()[0].name: arr}
        outs = self.sess.run(None, inputs)

        hash_output = self.seed.dot(outs[0].flatten())
        hash_bits = (hash_output >= 0)
        
        return hash_bits
    
    @staticmethod
    def bits2hex(bits: np.ndarray) -> str:
        int_arr = np.packbits(bits.astype(np.uint8).reshape((-1,4)), -1).squeeze() >> 4
        return "".join(f"{i:x}" for i in int_arr)
    
    @staticmethod
    def hex2bits(hex: str) -> np.ndarray:
        int_arr = np.array([int(i, 16) for i in hex], dtype=np.uint8)
        return np.unpackbits(np.expand_dims(int_arr, 1), -1)[:, -4:].reshape(-1).astype(bool)