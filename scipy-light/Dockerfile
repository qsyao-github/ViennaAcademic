FROM python:3.12-slim

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