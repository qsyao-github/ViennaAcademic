#! /usr/bin/bash
mamba update --all -y
mamba clean --all -f -y
rustup self update
rustup update stable
cd va_rust_utils
cargo upgrade -i
cargo update
cargo install-update -a
cargo cache -a
cd ../app
pip3 install -U --upgrade-strategy eager --no-cache-dir torch torchvision torchaudio -f https://mirrors.aliyun.com/pytorch-wheels/cu128
pip3 install -U --upgrade-strategy eager --no-cache-dir -r requirements.txt
pip cache purge