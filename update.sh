#! /usr/bin/bash
apt update && apt upgrade -y && apt autoremove -y
apt-get clean && rm -rf /var/lib/apt/lists/*
mamba update --all -y
mamba clean --all -f -y
rustup self update
rustup update stable
cd va_rust_utils
cargo upgrade -i
cargo update
cargo install-update -a
cargo clean
RUSTFLAGS='-C target-cpu=native' maturin develop
cargo cache -a
cd ../app
pip3 install -U --upgrade-strategy eager --no-cache-dir torch torchvision torchaudio -f https://mirrors.aliyun.com/pytorch-wheels/cu128 && pip3 install -U --upgrade-strategy eager --no-cache-dir -r requirements.txt
pip cache purge
rm -rf /tmp/* sudo rm -rf /var/tmp/*