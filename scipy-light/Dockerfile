FROM python:3.12-slim

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip3 install --no-cache-dir \
    'bottleneck' \
    'cython' \
    'dask' \
    'h5py' \
    'matplotlib' \
    'numba' \
    'numexpr' \
    'openpyxl' \
    'pandas' \
    'patsy' \
    'scikit-image' \
    'scikit-learn' \
    'scipy' \
    'seaborn' \
    'statsmodels' \
    'sympy' \
    'xlrd' \
    'ipython' \
    'numpy' && \
    useradd -m -s /bin/bash jovyan && \
    chown -R jovyan:jovyan /home/jovyan

USER jovyan
WORKDIR /home/jovyan

CMD ["tail", "-f", "/dev/null"]
