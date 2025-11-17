# import google storage
import json

from google.cloud import storage
import os

# Configuration
REGION = "us-central1"
BUCKET_NAME = "extracted_data_bucket"

def get_client_edi(customer_name: str) -> str:
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    storage_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
    config_bucket = storage_client.bucket(BUCKET_NAME)
    config_blob = config_bucket.blob(f"configs/company_sites.json")
    config_data = json.loads(config_blob.download_as_text())
    website_url = next((company["website"] for company in config_data["companies"] if
                            company["name"].lower() == customer_name.lower()), "")
    return website_url