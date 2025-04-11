#! /bin/bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate vienna_beta
conda install --update-all -c conda-forge pandoc
pip3 install -U --upgrade-strategy eager radon ruff
pip3 install -U --upgrade-strategy eager langchain langchain-community langchain-mistralai langgraph-checkpoint-sqlite langchain-openai langchain-deepseek langgraph gradio faiss-cpu arxiv docker unstructured markdown pymupdf4llm accelerate uvloop marker-pdf[full] crawl4ai