FROM python:3.11-slim

# OpenCV and image handling. opencv-python-headless still wants libGL present.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs the container as uid 1000. Without this the Hub cache and
# matplotlib both try to write to a home directory that is not writable, and
# the model download fails at startup rather than at build time.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    MPLCONFIGDIR=/tmp/mpl \
    CELLPOSE_LOCAL_MODELS_PATH=/home/user/.cellpose \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Torch is the bulk of the image; installing it from the CPU wheel index keeps
# the CUDA payload out and the image around a third of the size.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY --chown=user . .

USER user

EXPOSE 7860

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860", "--timeout-keep-alive", "120"]
