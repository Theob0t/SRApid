# Dockerfile
FROM ubuntu:24.04

LABEL maintainer="Theo Botella"
LABEL version="2.0"
LABEL description="Pipeline for SRA/GEO metadata and FASTQ download"

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PATH="/usr/local/bin:${PATH}"

# 1. System Dependencies & Certs
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    git \
    unzip \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    python3 \
    python3-pip \
    python3-venv \
    pigz \
    r-base \
    && update-ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install SRA Toolkit (fasterq-dump)
# Fetching specific version known to be stable or latest
RUN wget "https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/3.0.10/sratoolkit.3.0.10-ubuntu64.tar.gz" -O /tmp/sratoolkit.tar.gz \
    && tar -xvzf /tmp/sratoolkit.tar.gz -C /usr/local/ \
    && ln -s /usr/local/sratoolkit.3.0.10-ubuntu64/bin/* /usr/local/bin/ \
    && rm /tmp/sratoolkit.tar.gz \
    && fasterq-dump --version

# 3. Install Python Packages
# We create a virtual environment or install system-wide (using break-system-packages for container)
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# 4. Install R Packages (GEOmetadb)
RUN R -e "install.packages(c('DBI', 'RSQLite', 'optparse', 'BiocManager'), repos='https://cloud.r-project.org/')" \
    && R -e "BiocManager::install('GEOmetadb')"

# 5. Copy Source Code
COPY src/ /usr/local/src/
RUN chmod +x /usr/local/src/*.py /usr/local/src/*.R

# 6. Entrypoint
WORKDIR /data
ENTRYPOINT ["python3", "/usr/local/src/pipeline.py"]
CMD ["--help"]