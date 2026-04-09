# CARLA Counterfactual Framework — Python Client
# CARLA 0.9.10 は Ubuntu 18.04 向けビルドのため、同じベースイメージを使用。

# Stage 1: CARLA Python API (egg) を公式イメージから取得
FROM carlasim/carla:0.9.10 AS carla-source

# Stage 2: Python client (Ubuntu 18.04 ベース)
FROM ubuntu:18.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# Python 3.7 + 必要なシステムライブラリのインストール
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
        curl \
        ca-certificates \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.7 \
        python3.7-distutils \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libxerces-c3.2 \
        libpng16-16 \
        libjpeg-turbo8 \
        libtiff5 \
    && curl -sS https://bootstrap.pypa.io/pip/3.7/get-pip.py | python3.7 \
    && rm -rf /var/lib/apt/lists/*

# python / pip を python3.7 に向ける
RUN ln -sf /usr/bin/python3.7 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3.7 /usr/local/bin/python

# CARLA 0.9.10 Python API egg を site-packages へ
COPY --from=carla-source /home/carla/PythonAPI/carla/dist/ /tmp/carla_dist/
RUN SITE=$(python -c "import site; print(site.getsitepackages()[0])") \
    && EGG=$(ls /tmp/carla_dist/*.egg 2>/dev/null | head -1) \
    && cp "$EGG" "$SITE/" \
    && echo "$(basename "$EGG")" > "$SITE/carla.pth" \
    && rm -rf /tmp/carla_dist \
    && python -c "import carla; print('carla import OK')"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]
