#! /bin/bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate vienna_beta
conda install --update-all -c conda-forge pandoc
rustup self update
rustup update stable
$HOME/typst-x86_64-unknown-linux-musl/typst update
pip3 install -U --upgrade-strategy eager radon ruff langchain langchain-community langchain-mistralai langgraph-checkpoint-sqlite langchain-openai langchain-deepseek langgraph gradio faiss-cpu arxiv docker unstructured markdown pymupdf4llm uvloop crawl4ai maturin marker-pdf[full]