# CARLA Counterfactual Framework — Python Client
# h5py の PyPI wheel は HDF5 を内包しているので libhdf5-dev は不要。
# matplotlib/mplsoccer の描画バックエンド用に libgl1 のみ必要。

# Stage 1: CARLA Python API (egg) を公式イメージから取得
FROM carlasim/carla:0.9.10 AS carla-source

# Stage 2: Python client
FROM python:3.7-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libxerces-c3.2 \
    && rm -rf /var/lib/apt/lists/*

# CARLA 0.9.10 Python API egg を site-packages に追加
COPY --from=carla-source /home/carla/PythonAPI/carla/dist/ /tmp/carla_dist/
RUN SITE=$(python -c "import site; print(site.getsitepackages()[0])") && \
    EGG=$(ls /tmp/carla_dist/*.egg 2>/dev/null | head -1) && \
    cp "$EGG" "$SITE/" && \
    echo "$(basename $EGG)" > "$SITE/carla.pth" && \
    rm -rf /tmp/carla_dist

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]
