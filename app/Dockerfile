FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

ENV PATH="/root/conda/bin:/root/.cargo/bin:${PATH}" \
    HOME="/root" \
    RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static \
    RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup

COPY requirements.txt /root/requirements.txt

# apt镜像
RUN sed -i 's@archive.ubuntu.com@mirrors.sustech.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's@security.ubuntu.com@mirrors.sustech.edu.cn@g' /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    ## miniforge & rust
    wget \
    curl \
    pkg-config \
    libssl-dev \
    build-essential \
    ## typst
    fontconfig \ 
    fonts-noto-cjk \
    ## postgres
    libpq-dev \
    ## 文件类型验证
    libmagic1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# miniforge
RUN wget -O Miniforge3.sh "https://mirror.nju.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-$(uname)-$(uname -m).sh" && \
    bash Miniforge3.sh -b -p "${HOME}/conda" && \
    . "${HOME}/conda/etc/profile.d/conda.sh" && \
    . "${HOME}/conda/etc/profile.d/mamba.sh" && \
    rm Miniforge3.sh && \
    # Conda镜像
    ${HOME}/conda/bin/conda config --add channels https://mirrors.sustech.edu.cn/anaconda/pkgs/main && \
    ${HOME}/conda/bin/conda config --add channels https://mirrors.sustech.edu.cn/anaconda/pkgs/r && \
    ${HOME}/conda/bin/conda config --add channels https://mirrors.sustech.edu.cn/anaconda/pkgs/msys2 && \
    conda config --set custom_channels.conda-forge https://mirrors.sustech.edu.cn/anaconda/cloud/ && \
    # 配置conda & mamba
    ${HOME}/conda/bin/conda init bash && \
    ${HOME}/conda/bin/mamba shell init --shell bash --root-prefix=${HOME}/.local/share/mamba && \
    echo "eval \"\$(${HOME}/conda/bin/mamba shell hook --shell bash)\"" >> ${HOME}/.bashrc && \
    echo "conda activate vienna_beta" >> ${HOME}/.bashrc
# python虚拟环境 & pandoc
RUN mamba create -n vienna_beta python=3.12 pandoc
# pip镜像 & 依赖
RUN mamba run -n vienna_beta pip3 config set global.index-url https://mirrors.sustech.edu.cn/pypi/simple && \
    mamba run -n vienna_beta pip3 install --no-cache-dir torch torchvision torchaudio
RUN mamba run -n vienna_beta pip3 install --no-cache-dir -r /root/requirements.txt && \
    mamba clean --all -f -y && \
    rm /root/requirements.txt
# Rust & typst
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env" && \
    echo '[source.crates-io]\nreplace-with = "ustc"\n\n[source.ustc]\nregistry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"\n\n[registries.ustc]\nindex = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"' > root/.cargo/config.toml
RUN cargo install --locked typst-cli
# 更多cargo工具
RUN cargo install cargo-update cargo-cache cargo-edit && \
    cargo cache -a

WORKDIR /root

CMD ["tail", "-f", "/dev/null"]
