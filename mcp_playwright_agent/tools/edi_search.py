import json
import logging

from mcp_playwright_agent.tools.utils import BUCKET_NAME, CONFIG_BLOB_PATH, get_cached_lookup_dict
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

def get_client_edi(customer_name: str) -> str:
    """
    Fetch company configuration from GCS and return the website URL for the given customer_name.
    """

    logger.info(f"Looking up EDI for: {customer_name} in bucket {BUCKET_NAME}")

    try:
        companies = get_cached_lookup_dict(BUCKET_NAME, CONFIG_BLOB_PATH)
        company = companies.get(customer_name.lower())

        if company:
            website = company.get("website", "")
            return f"Found website for {customer_name}: {website}"
        else:
            return f"Customer '{customer_name}' not found."

    except google_exceptions.NotFound:
        msg = f"Config file not found in bucket {BUCKET_NAME}: {CONFIG_BLOB_PATH}"
        logger.error(msg)
        return f"Error: {msg}"
    except json.JSONDecodeError:
        msg = f"Invalid JSON in config file {CONFIG_BLOB_PATH}"
        logger.error(msg)
        return f"Error: {msg}"
    except Exception as e:
        logger.exception("Unexpected error in get_client_edi")
        return f"Error retrieving data: {str(e)}"