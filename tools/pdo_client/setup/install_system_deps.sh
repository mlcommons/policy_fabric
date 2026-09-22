set -e
# System packages + wasi-sdk needed to build the PDO client and contracts.
# Run as root (e.g. a Dockerfile RUN step, or `sudo` on bare metal).
export DEBIAN_FRONTEND=noninteractive

apt update && apt install -y cmake curl git pkg-config unzip xxd libssl-dev build-essential
apt install -y swig python3 python3-dev python3-venv virtualenv
apt install -y liblmdb-dev libprotobuf-dev libsecp256k1-dev protobuf-compiler libncurses5-dev
apt install -y wget curl

wget -q -P /tmp https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-27/wasi-sdk-27.0-x86_64-linux.deb
dpkg --install /tmp/wasi-sdk-27.0-x86_64-linux.deb
