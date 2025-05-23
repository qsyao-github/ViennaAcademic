#!/bin/bash
source /root/conda/etc/profile.d/conda.sh
conda activate vienna_beta
mamba update --all
mamba clean --all -f -y
rustup self update
rustup update stable
cargo install-update -a
cargo cache -a
pip3 install -U --upgrade-strategy eager --no-cache-dir -r requirements.txt -i https://pypi.org/simple
pip cache purge