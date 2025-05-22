FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04

ENV PATH="/root/conda/bin:/root/.cargo/bin:${PATH}" \
    HOME="/root"

COPY requirements.txt /root/requirements.txt

# apt镜像
RUN sed -i 's@archive.ubuntu.com@mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@security.ubuntu.com@mirrors.aliyun.com@g' /etc/apt/sources.list && \
    # apt
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
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # miniforge
    wget -O Miniforge3.sh "https://bgithub.xyz/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" && \
    bash Miniforge3.sh -b -p "${HOME}/conda" && \
    . "${HOME}/conda/etc/profile.d/conda.sh" && \
    . "${HOME}/conda/etc/profile.d/mamba.sh" && \
    rm Miniforge3.sh && \
    # Conda镜像
    # ${HOME}/conda/bin/conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main && \
    # ${HOME}/conda/bin/conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r && \
    # ${HOME}/conda/bin/conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2 && \
    # ${HOME}/conda/bin/conda config --set show_channel_urls yes && \
    # 配置conda & mamba
    ${HOME}/conda/bin/conda init bash && \
    ${HOME}/conda/bin/mamba shell init --shell bash --root-prefix=${HOME}/.local/share/mamba && \
    echo "eval \"\$(${HOME}/conda/bin/mamba shell hook --shell bash)\"" >> ${HOME}/.bashrc && \
    echo "conda activate vienna_beta" >> ${HOME}/.bashrc && \
    # python虚拟环境 & pandoc
    mamba create -n vienna_beta python=3.12 pandoc && \
    # pip镜像 & 依赖
    mamba run -n vienna_beta pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    mamba run -n vienna_beta pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 && \
    mamba run -n vienna_beta pip3 install --no-cache-dir -r /root/requirements.txt && \
    mamba clean --all -f -y && \
    rm /root/requirements.txt && \
    # Rust & typst
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env" && \
    cargo install --locked typst-cli

WORKDIR /root

CMD ["tail", "-f", "/dev/null"]
