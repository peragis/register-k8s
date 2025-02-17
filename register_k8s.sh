#!/bin/bash

# Function to extract the full URL (including protocol and port)
extract_url() {
  echo "$1"
}

# Function to apply the YAML manifest
apply_manifest() {

  local token="$1"
  local cluster_name="$2"
  local k8s_api="$3"

  local API_SERVER='https://api.peragis.ai'	
  # Construct the URL with parameters
  manifest_url="${API_SERVER}/kubernetes-yaml?api-token=${token}&k8s-cluster-name=${cluster_name}&k8s-api=${k8s_api}"

  echo $manifest_url
  # Apply the manifest using curl and kubectl
  kubectl apply -f $manifest_url

  if [[ $? -eq 0 ]]; then
    echo "Manifest applied successfully."
    exit 0
  else
    echo "Error applying manifest."
    exit 1
  fi
}


# Check for required parameters (token and cluster_name)
if [[ $# -lt 2 ]]; then  # Allow k8s_api to be fetched
  echo "Usage: $0 <token> <cluster_name> [<k8s_api>]"
  exit 1
fi

token="$1"
cluster_name="$2"

# Get the API server address.  Try cluster-info first, then config view
k8s_api=$(kubectl cluster-info 2>/dev/null | grep 'Kubernetes master' | awk '{print $NF}')

if [[ -z "$k8s_api" ]]; then
    k8s_api=$(kubectl config view -o json 2>/dev/null | jq -r '.clusters[0].cluster.server')
    if [[ -z "$k8s_api" ]]; then
      k8s_api=$(kubectl config view -o yaml 2>/dev/null | yq e '.clusters[0].cluster.server')
      if [[ -z "$k8s_api" ]]; then
        echo "Error: Could not retrieve API server address from cluster-info or config view (json or yaml)."
        exit 1
      fi
    fi
fi

# If the user provided an k8s_api, overwrite the fetched one
if [[ $# -eq 3 ]]; then
  k8s_api="$3"
fi

apply_manifest "$token" "$cluster_name" "$k8s_api"
