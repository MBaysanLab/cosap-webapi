FROM debian:bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

SHELL [ "/bin/bash", "--login", "-c" ]

RUN apt update && apt install -y wget git

# Install Miniconda
# We exclusively support x86_64 at the moment since some packages are not yet available for other architectures.
WORKDIR /tmp
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /app/miniconda && rm Miniconda3-latest-Linux-x86_64.sh
ENV PATH="/app/miniconda/bin:${PATH}"
RUN echo export PATH="/app/miniconda/bin:${PATH}" >> ~/.bashrc && echo ". ~/.bashrc" >> ~/.bash_profile
RUN conda init bash

# Install CoSAP
WORKDIR /app
RUN git clone --recursive --single-branch --branch develop https://github.com/MBaysanLab/cosap.git

WORKDIR /app/cosap
RUN conda install -c conda-forge mamba \
    && mamba env create -f environments/default_environment.yml
RUN echo "conda activate cosap" >> ~/.bashrc
RUN pip install . 

# Install web API requirements
RUN pip install Django==4.0 djangorestframework django-filter django-countries psycopg2-binary django-cors-headers "celery[redis]"

WORKDIR /app/webapi