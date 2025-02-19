import os
import argparse
import requests
import json
from kubernetes import client, config

def get_service_account_token(namespace, service_account_name):
    """Retrieves the token for a service account."""
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    api = client.CoreV1Api()

    try:
        sa = api.read_namespaced_service_account(name=service_account_name, namespace=namespace)
        secrets = sa.secrets

        if secrets:
            for secret in secrets:
                secret_name = secret.name
                secret = api.read_namespaced_secret(name=secret_name, namespace=namespace)
                if secret.type == "kubernetes.io/service-account-token":
                    token = secret.data.get('token')
                    if token:
                        return token  # No need to decode anymore!
                    else:
                        print(f"Error: Could not find 'token' in secret '{secret_name}'.")

            print(f"Error: No token secret found for service account '{service_account_name}'.")
        else:
            print(f"Error: Service account '{service_account_name}' has no secrets.")

    except client.ApiException as e:
        print(f"Error retrieving service account token: {e}")
    return None

def make_api_request(api_url, header_name, api_token, payload):
    """Makes a POST request to the specified API."""

    headers = {
        header_name: api_token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        print("API request successful:")
        try:
            print(json.dumps(response.json(), indent=4)) # Print JSON nicely formatted
        except json.JSONDecodeError:
            print(response.text)  # Fallback to printing raw text

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        if response:
            print(f"Response status code: {response.status_code}")
            try:
                print(f"Response content: {response.text}")
            except:
                pass
        raise  # Re-raise the exception after printing info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kubernetes integration script.")

    # API parameters
    parser.add_argument("--api-url", dest="api_url", default=os.environ.get("API_URL"), help="API URL (env: API_URL)")
    parser.add_argument("--header-name", dest="header_name", default=os.environ.get("HEADER_NAME", "X-API-Token"), help="Header name for token (env: HEADER_NAME, default: X-API-Token)")
    parser.add_argument("--api-token", dest="api_token", default=os.environ.get("API_TOKEN"), help="API token (env: API_TOKEN)")
    parser.add_argument("--payload", dest="payload_str", default=os.environ.get("PAYLOAD", "{}"), help="JSON payload string (env: PAYLOAD, default: {})")

    # Kubernetes parameters
    parser.add_argument("--namespace", dest="namespace", default=os.environ.get("NAMESPACE", "default"), help="Kubernetes namespace (env: NAMESPACE, default: default)")
    parser.add_argument("--service-account-name", dest="service_account_name", default=os.environ.get("SERVICE_ACCOUNT_NAME", "default"), help="Service account name (env: SERVICE_ACCOUNT_NAME, default: default)")
    parser.add_argument("--k8s-api-url", dest="k8s_api_url", default=os.environ.get("K8S_API_URL", "https://127.0.0.1"), help="External Kubernetes API address")

    args = parser.parse_args()

    if not args.api_url or not args.api_token:
        print("Error: --api-url and --api-token are required (or set API_URL and API_TOKEN env vars).")
        exit(1)

    service_token = get_service_account_token(args.namespace, args.service_account_name)
    
    if service_token:
        try:
            payload = json.loads(args.payload_str)  # Load base payload
        except json.JSONDecodeError as e:
            print(f"Error decoding payload JSON: {e}")
            exit(1)

        payload['secret'] = service_token  # Add the token to the payload

    else:
        print("Failed to retrieve service account token. Exiting.")
        exit(1)

    payload['asset_data'] = dict()
    payload['asset_data']['api_address'] = args.k8s_api_url

    try:
        make_api_request(args.api_url, args.header_name, args.api_token, payload)
    except Exception as e:  # Catch and handle any exceptions during the API request
        print(f"An error occurred during API request: {e}")
        exit(1)




