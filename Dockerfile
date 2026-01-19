FROM continuumio/miniconda3:latest # 带有CUDA的conda基础镜像

WORKDIR /app
# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    unixodbc \
    unixodbc-dev \
    freetds-bin \
    freetds-dev \
    tdsodbc \
    libssl-dev \
    libffi-dev \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*
RUN conda create -n agent python=3.10 -y

COPY requirements.txt .
RUN /opt/conda/envs/agent/bin/pip install \
    --no-cache-dir \
    -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN /opt/conda/envs/agent/bin/pip install lmdeploy -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY a2w/ ./a2w/
COPY data/ ./data/
COPY init-sqlserver.sh /app/init-sqlserver.sh
COPY start_app.sh /app/start_app.sh

RUN chmod +x /app/init-db.sh /app/start_app.sh
EXPOSE 7312

CMD ["/app/start_app.sh"]