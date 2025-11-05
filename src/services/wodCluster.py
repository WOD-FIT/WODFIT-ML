import hashlib
import json
import logging
import os
import pickle
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
import scipy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

try:  # pragma: no cover - optional dependency guard
    import redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    redis = None  # type: ignore
    RedisError = Exception  # type: ignore

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))         # .../src/services
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))  # .../WodCluster

MODEL_PATH = os.path.join(PROJECT_ROOT, "models/0.214/model_vectorizer_scaler.dump")

with open(MODEL_PATH, "rb") as f:
    loaded_model = pickle.load(f)
    wod_cluster: KNeighborsClassifier = loaded_model["model"]
    vectorizer: TfidfVectorizer = loaded_model["vectorizer"]
    scaler: StandardScaler = loaded_model["scaler"]


logger = logging.getLogger(__name__)


def _parse_cache_ttl(value: Optional[str]) -> int:
    try:
        ttl = int(value) if value is not None else 3600
    except ValueError:
        logger.warning(
            "Invalid WOD_CLUSTER_CACHE_TTL value '%s'. Falling back to 3600 seconds.",
            value,
        )
        ttl = 3600
    return max(ttl, 0)


REDIS_URL = os.getenv("REDIS_URL")
CACHE_TTL_SECONDS = _parse_cache_ttl(os.getenv("WOD_CLUSTER_CACHE_TTL"))

_cache_client: Optional["redis.Redis"] = None

if REDIS_URL and redis is not None:
    try:
        _cache_client = redis.Redis.from_url(REDIS_URL)
    except (RedisError, ValueError) as exc:  # pragma: no cover - connection error at import time
        logger.error("Failed to create Redis client: %s", exc)
        _cache_client = None


def _ensure_iterable(name: str, values: Iterable) -> Sequence:
    if isinstance(values, (list, tuple)):
        return list(values)
    if isinstance(values, np.ndarray):
        return values.tolist()
    raise ValueError(f"{name} must be provided as a list.")


def _validate_wods(wods: Sequence[str]) -> list[str]:
    if not wods:
        raise ValueError("At least one workout description must be provided.")

    cleaned_wods: list[str] = []
    for idx, wod in enumerate(wods):
        if not isinstance(wod, str):
            raise ValueError(f"wods[{idx}] must be a string.")
        cleaned = wod.strip()
        if not cleaned:
            raise ValueError("Workout descriptions cannot be empty strings.")
        cleaned_wods.append(cleaned)

    return cleaned_wods


def _validate_weights(weights: Sequence[float], expected_length: int) -> np.ndarray:
    if not weights:
        raise ValueError("At least one workout weight must be provided.")
    if len(weights) != expected_length:
        raise ValueError("The number of weights must match the number of workouts.")

    try:
        weights_array = np.asarray(weights, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Weights must be numeric values.") from exc

    if not np.isfinite(weights_array).all():
        raise ValueError("Weights must be finite numbers.")

    return weights_array.reshape(-1, 1)


def _validate_inputs(wods: Iterable[str], weights: Iterable[float]) -> Tuple[list[str], np.ndarray]:
    validated_wods = _validate_wods(_ensure_iterable("wods", wods))
    validated_weights = _validate_weights(_ensure_iterable("weights", weights), len(validated_wods))
    return validated_wods, validated_weights


def _prepare_features(validated_wods: list[str], validated_weights: np.ndarray):
    tfidf_vec = vectorizer.transform(validated_wods)
    scaled_weights = scaler.transform(validated_weights)
    return scipy.sparse.hstack([tfidf_vec, scaled_weights])


def preprocess(wods: list[str], weights: list[float]):
    """Preprocess workouts for model inference.

    The function validates the incoming workouts and weights before applying the
    TF-IDF vectorizer and weight scaler. A ``ValueError`` is raised when the
    inputs do not satisfy the expected format so that callers can surface a
    meaningful error to the API consumer.
    """

    validated_wods, validated_weights = _validate_inputs(wods, weights)
    return _prepare_features(validated_wods, validated_weights)


def _build_cache_key(wods: list[str], weights: list[float]) -> str:
    payload = json.dumps({"wods": wods, "weights": weights}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"wod-cluster:{digest}"


def _fetch_cached_predictions(cache_key: str) -> Optional[list[int]]:
    if _cache_client is None:
        return None
    try:
        cached = _cache_client.get(cache_key)
    except RedisError as exc:  # pragma: no cover - network failure
        logger.warning("Redis get failed for key %s: %s", cache_key, exc)
        return None
    if cached is None:
        return None
    if isinstance(cached, (bytes, bytearray, memoryview)):
        cached = bytes(cached).decode("utf-8")
    try:
        data = json.loads(cached)
    except (TypeError, json.JSONDecodeError):
        logger.debug("Invalid JSON payload in cache for key %s", cache_key)
        return None
    if isinstance(data, list):
        return data
    logger.debug("Unexpected cache payload type for key %s: %s", cache_key, type(data))
    return None


def _store_cached_predictions(cache_key: str, predictions: list[int]) -> None:
    if _cache_client is None:
        return
    try:
        payload = json.dumps(predictions)
        if CACHE_TTL_SECONDS > 0:
            _cache_client.setex(cache_key, CACHE_TTL_SECONDS, payload)
        else:
            _cache_client.set(cache_key, payload)
    except RedisError as exc:  # pragma: no cover - network failure
        logger.warning("Redis set failed for key %s: %s", cache_key, exc)


def predictCluster(wods: list[str], weights: list[float]):
    validated_wods, validated_weights = _validate_inputs(wods, weights)
    normalized_weights = validated_weights.reshape(-1).astype(float).tolist()
    cache_key = _build_cache_key(validated_wods, normalized_weights)

    cached_predictions = _fetch_cached_predictions(cache_key)
    if cached_predictions is not None:
        return cached_predictions

    processed = _prepare_features(validated_wods, validated_weights)
    preds = wod_cluster.predict(processed).tolist()
    _store_cached_predictions(cache_key, preds)
    return preds
