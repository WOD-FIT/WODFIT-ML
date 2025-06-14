import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import scipy
import pickle
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))         # .../src/services
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))  # .../WodCluster

MODEL_PATH = os.path.join(PROJECT_ROOT, "models/0.214/model_vectorizer_scaler.dump")

with open(MODEL_PATH, "rb") as f:
    loaded_model = pickle.load(f)
    wod_cluster: KNeighborsClassifier = loaded_model['model']
    vectorizer: TfidfVectorizer = loaded_model['vectorizer']
    scaler: StandardScaler = loaded_model['scaler']


def preprocess(wods: list[str], weights: list[float]):
    tfidf_vec = vectorizer.transform(wods)
    scaled_weights = scaler.transform(np.array(weights).reshape(-1, 1))
    vec = scipy.sparse.hstack([tfidf_vec, scaled_weights])
    return vec

def predictCluster(wods: list[str], weights: list[float]):
    processed = preprocess(wods, weights)
    preds = wod_cluster.predict(processed)
    return preds.tolist()
