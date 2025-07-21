#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# minikube start --memory no-limit

helm repo add crossplane-stable https://charts.crossplane.io/stable || true
helm repo update
helm install crossplane \
    --namespace crossplane-system \
    --create-namespace crossplane-stable/crossplane || true

kubectl apply -f ${SCRIPT_DIR}/provider.yaml
# kubectl apply -f ${SCRIPT_DIR}/providerconfig.yaml
