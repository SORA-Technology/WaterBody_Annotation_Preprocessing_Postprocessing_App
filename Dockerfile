FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    libgdal-dev \
    python3-opencv \
    libgl1-mesa-glx \
    gdal-bin \
    libspatialindex-dev \
    && rm -rf /var/lib/apt/lists/* 

# upgrade pip to latest 
RUN python -m pip install --upgrade pip

# set working directory
WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501

# launch streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501"]


