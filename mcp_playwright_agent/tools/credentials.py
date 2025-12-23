import json
import logging

from mcp_playwright_agent.tools.utils import PROJECT_ID, get_cached_lookup_dict, BUCKET_NAME, CONFIG_BLOB_PATH, \
    get_secret_client

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)


def get_customer_credentials(customer_name: str) -> str:
    """
    Retrieves credentials (company_code, user_id, password) for a customer.
    Returns sensitive data - use carefully.
    """
    project_id = PROJECT_ID

    if not project_id:
        try:
            import google.auth
            _, project_id = google.auth.default()
        except:
            pass

    if not project_id:
        return "Error: Could not determine Google Cloud Project ID"

    try:
        companies = get_cached_lookup_dict(BUCKET_NAME, CONFIG_BLOB_PATH)
        company = companies.get(customer_name.lower())

        if not company:
            return f"Customer '{customer_name}' not found in config."

        secret_client = get_secret_client()
        keywords = company.get("keywords", [])
        search_keywords = keywords + [company.get("name", "")]

        logs = []

        for keyword in search_keywords:
            if not keyword:
                continue

            safe_keyword = keyword.lower().strip().replace(' ', '_')
            secret_name = f"projects/{project_id}/secrets/{safe_keyword}_credentials/versions/latest"

            try:
                logger.info(f"Attempting to fetch secret: {safe_keyword}_credentials")
                response = secret_client.access_secret_version(name=secret_name)

                secret_payload = response.payload.data.decode("UTF-8")
                creds = json.loads(secret_payload)

                code = creds.get("company_code") or "N/A"
                user_id = creds.get("user_id") or "N/A"
                password = creds.get("password") or "N/A"

                return json.dumps({
                    "company_code": code,
                    "user_id": user_id,
                    "password": password
                })


            except Exception as e:
                error_msg = f"Failed '{safe_keyword}': {type(e).__name__} - {str(e)}"
                logger.warning(error_msg)
                logs.append(error_msg)
                continue

        return f"No credentials found. Details: {'; '.join(logs)}"

    except Exception as e:
        logger.exception("Error in get_customer_credentials")
        return f"Error: {str(e)}"

def demo_get_customer_credentials(customer_name: str) -> str:
    """
    Demo version of get_customer_credentials that returns dummy data.
    """
    dummy_data = {
        "company_code": "0289",
        "user_id": "asai",
        "password": "NMTJ2023%"
    }
    return json.dumps(dummy_data)