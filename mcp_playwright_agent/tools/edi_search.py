# python
import json
import os
import logging
from typing import Optional

from google.cloud import storage
from google.api_core import exceptions as google_exceptions

REGION = "us-central1"
BUCKET_NAME = "extracted_data_bucket"
_CONFIG_BLOB_PATH = "configs/company_sites.json"


def get_client_edi(
    customer_name: str,
    project: Optional[str] = None,
    bucket_name: str = BUCKET_NAME,
) -> str:
    """
    Fetch company_sites JSON from GCS and return the website for `customer_name`.
    Returns empty string if not found or on recoverable errors.
    """
    project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
    storage_client = storage.Client(project=project)

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(_CONFIG_BLOB_PATH)
        # download_as_text will raise if blob does not exist / no permission
        text = blob.download_as_text()
        config_data = json.loads(text)
        companies = config_data.get("companies", [])
        website = next(
            (c.get("website", "") for c in companies if c.get("name", "").lower() == customer_name.lower()),
            "",
        )
        return website or ""
    except google_exceptions.NotFound:
        logging.info("Config blob not found in bucket %s: %s", bucket_name, _CONFIG_BLOB_PATH)
        return ""
    except json.JSONDecodeError:
        logging.exception("Invalid JSON in config blob %s/%s", bucket_name, _CONFIG_BLOB_PATH)
        return ""
    except google_exceptions.GoogleAPICallError:
        logging.exception("GCS API error while reading %s/%s", bucket_name, _CONFIG_BLOB_PATH)
        return ""
    except Exception:
        logging.exception("Unexpected error in get_client_edi")
        raise