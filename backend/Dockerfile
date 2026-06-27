# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (torch wheels bundle their own libs; libglib/libgl1 needed by CV/PIL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# basicsr imports torchvision.transforms.functional_tensor, removed in
# torchvision>=0.17. Provide a shim that re-exports from torchvision.transforms
# so basicsr's data.degradations import resolves.
RUN python -c "import pathlib, torchvision; d=pathlib.Path(torchvision.__file__).parent/'transforms'; (d/'functional_tensor.py').write_text('from torchvision.transforms.functional import rgb_to_grayscale\n')"

COPY . .

# Directory for downloaded model weights (populated at runtime by entrypoint).
RUN mkdir -p /app/models /app/results /app/uploads

EXPOSE 80

# Entrypoint ensures model weights are present, then execs the given command
# (default: uvicorn). For the worker service, docker-compose passes
# "celery -A app.worker worker ..." as the command.
ENTRYPOINT ["python", "app/entrypoint.py"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]