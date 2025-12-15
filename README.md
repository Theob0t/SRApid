# SRApid Pipeline

<div align="center">

<pre>
   _____ _____                  _     _ 
  / ____|  __ \     /\         (_)   | |
 | (___ | |__) |   /  \   _ __  _  __| |
  \___ \|  _  /   / /\ \ | '_ \| |/ _` |
  ____) | | \ \  / ____ \| |_) | | (_| |
 |_____/|_|  \_\/_/    \_\ .__/|_|\__,_|
                         | |            
                         |_|            
</pre>

**_Because life is too short to wait for `fastq-dump`._**

<br />

[![CI/CD Pipeline](https://github.com/Theob0t/SRApid/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Theob0t/SRApid/actions/workflows/pipeline.yml)
[![Container Registry](https://img.shields.io/badge/Container-GHCR-blue?logo=github)](https://github.com/Theob0t/SRApid/pkgs/container/srapid)
[![Docker Publish](https://github.com/Theob0t/SRApid/actions/workflows/publish.yml/badge.svg)](https://github.com/Theob0t/SRApid/actions/workflows/publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![R](https://img.shields.io/badge/R-4.0+-blue.svg)](https://www.r-project.org/)

</div>

**SRApid** ("SRA-Rapid") is a containerized pipeline designed for HPC environments. It automates the retrieval of paired technical (SRA) and biological (GEO) metadata, alongside raw FASTQ sequencing data, using a highly optimized parallelized approach.


## Requirements

1. **Docker** (Local) or **Apptainer/Singularity** (HPC).
2. **Databases** (Optional but recommended for speed):
   - `SRAmetadb.sqlite`
   - `GEOmetadb.sqlite`

## Setup

### 1. Build Container
```bash
docker build -t SRApid:latest .
# OR for HPC
apptainer build SRApid.sif docker-daemon://SRApid:latest
```

### 2. Prepare Data
Create a file `GSE.txt`:
```text
GSE76511
GSE49642
```

## Usage

### Local (Docker)
```bash
# Assuming DBs are in current folder
docker run --rm -v $(pwd):/data SRApid:latest \
    --gse_list GSE.txt \
    --out_dir ./output \
    --sra_db SRAmetadb.sqlite \
    --geo_db GEOmetadb.sqlite \
    --cpus 8
```

### HPC (Apptainer)
```bash
apptainer exec --bind /gpfs:/gpfs SRApid.sif \
    python3 /usr/local/src/pipeline.py \
    --gse_list GSE.txt \
    --out_dir /gpfs/path/to/output \
    --sra_db /gpfs/path/to/SRAmetadb.sqlite \
    --geo_db /gpfs/path/to/GEOmetadb.sqlite \
    --cpus 16
```

## Outputs
- `technical_metadata/`: CSVs with SRA run info.
- `biological_metadata/metadata/`: CSVs for individual GSMs.
- `fastq/`: Folder per SRR containing `_R1.fastq.gz` (and R2 if paired).
- `GSE_run_counts.csv`: Summary report.

