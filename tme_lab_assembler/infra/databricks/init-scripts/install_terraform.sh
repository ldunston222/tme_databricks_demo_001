#!/usr/bin/env bash
set -euo pipefail

# Databricks cluster init script (Azure DBR 17.3 LTS)
# Installs Terraform on the driver so notebooks can call `terraform`.
#
# Attach this script to your cluster (Compute -> <cluster> -> Advanced options -> Init Scripts)
# or to a Job cluster (Jobs -> <job> -> Edit -> Job cluster -> Advanced options -> Init Scripts).

TERRAFORM_VERSION="${TERRAFORM_VERSION:-1.8.5}"
INSTALL_DIR="${TERRAFORM_INSTALL_DIR:-/usr/local/bin}"

arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) tf_arch="amd64" ;;
  aarch64|arm64) tf_arch="arm64" ;;
  *) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
esac

# Databricks runtimes are Linux; use linux_<arch>
zip="terraform_${TERRAFORM_VERSION}_linux_${tf_arch}.zip"
url="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/${zip}"

if command -v terraform >/dev/null 2>&1; then
  echo "terraform already present: $(terraform version | head -n 1)"
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found; cannot download terraform" >&2
  exit 1
fi

workdir="/tmp/terraform-install"
rm -rf "$workdir"
mkdir -p "$workdir"
cd "$workdir"

echo "Downloading Terraform ${TERRAFORM_VERSION} from ${url}"
curl -fsSLo "$zip" "$url"

if ! command -v unzip >/dev/null 2>&1; then
  echo "unzip not found; attempting to install (requires sudo)" >&2
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y unzip
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y unzip
  else
    echo "No supported package manager found to install unzip" >&2
    exit 1
  fi
fi

unzip -q "$zip"
chmod +x terraform

sudo mkdir -p "$INSTALL_DIR"
sudo mv terraform "$INSTALL_DIR/terraform"

echo "Installed: $($INSTALL_DIR/terraform version | head -n 1)"
