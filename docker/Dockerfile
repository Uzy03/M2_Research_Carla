# CARLA Counterfactual Framework — Python Client
# h5py の PyPI wheel は HDF5 を内包しているので libhdf5-dev は不要。
# matplotlib/mplsoccer の描画バックエンド用に libgl1 のみ必要。

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]
