FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    libgdal-dev \
    gdal-bin \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/*

# set working directory
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# launch streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501"]


