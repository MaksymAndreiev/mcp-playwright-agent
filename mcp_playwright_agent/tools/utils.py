import json
import logging
import os
import time

from google.cloud import storage, secretmanager

BUCKET_NAME = "extracted_data_bucket"
CONFIG_BLOB_PATH = "configs/company_sites.json"
PROJECT_ID = "capstonec06-474100"

_STORAGE_CLIENT = None
_SECRET_CLIENT = None

_CONFIG_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 300  # Кешуємо конфіг на 5 хвилин (300 сек)

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

def get_storage_client():
    global _STORAGE_CLIENT
    if _STORAGE_CLIENT is None:
        project_id = PROJECT_ID
        if not project_id:
            try:
                import google.auth
                _, project_id = google.auth.default()
            except Exception as e:
                logger.warning(f"Could not determine project ID automatically: {e}")

        logger.info(f"Initializing GCS Client for project: {project_id}")
        _STORAGE_CLIENT = storage.Client(project=project_id)

    return _STORAGE_CLIENT

def get_cached_lookup_dict(bucket_name, blob_path):
    now = time.time()

    if _CONFIG_CACHE["data"] and (now - _CONFIG_CACHE["timestamp"] < CACHE_TTL):
        return _CONFIG_CACHE["data"]

    logger.info(f"Fetching config from GCS bucket: {bucket_name}")
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    try:
        text = blob.download_as_text(encoding="utf-8")
        raw_json = json.loads(text)
        companies_list = raw_json.get("companies", [])

        optimized_dict = {
            c.get("name", "").lower(): c
            for c in companies_list
        }

        _CONFIG_CACHE["data"] = optimized_dict
        _CONFIG_CACHE["timestamp"] = now
        logger.info(f"Config loaded successfully. Found {len(optimized_dict)} companies.")
        return optimized_dict

    except Exception as e:
        _CONFIG_CACHE["data"] = None
        _CONFIG_CACHE["timestamp"] = 0
        logger.exception("Error loading config from GCS")
        raise e

def get_secret_client():
    global _SECRET_CLIENT
    if _SECRET_CLIENT is None:
        logger.info("Initializing Secret Manager Client")
        _SECRET_CLIENT = secretmanager.SecretManagerServiceClient()
    return _SECRET_CLIENT