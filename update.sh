#! /bin/bash
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate vienna_beta
conda install --update-all -c conda-forge pandoc
pip3 install -U --upgrade-strategy eager radon ruff
pip3 install -U --upgrade-strategy eager langchain langchain-community langchain-mistralai langchain-openai langchain-deepseek langgraph gradio numpy scipy sympy matplotlib ipython faiss-cpu arxiv docker unstructured markdown pymupdf4llm accelerate uvloop
pip3 install -U --upgrade-strategy eager marker-pdf[full] crawl4ai