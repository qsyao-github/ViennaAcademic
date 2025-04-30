FROM python:3.12-slim

RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf

RUN pip install \
    'beautifulsoup4' \
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
    'protobuf' \
    'scikit-image' \
    'scikit-learn' \
    'scipy' \
    'seaborn' \
    'statsmodels' \
    'sympy' \
    'xlrd' \
    'ipython' \
    'numpy' && \
    pip cache purge

ENV HOME="/home/jovyan"

RUN useradd -m -s /bin/bash jovyan && \
    mkdir -p ${HOME}/work && \
    chown -R jovyan:jovyan ${HOME}

USER jovyan
WORKDIR ${HOME}

CMD ["tail", "-f", "/dev/null"]