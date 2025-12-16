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
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![R](https://img.shields.io/badge/R-4.0+-blue.svg)](https://www.r-project.org/)

</div>

**SRApid** ("SRA-Rapid") is a containerized pipeline designed for HPC environments. It automates the retrieval of paired technical (SRA) and biological (GEO) metadata, alongside raw FASTQ sequencing data, using a highly optimized parallelized approach.

---

## ⚠️ Important: Input Format (SRP vs GSE)

**SRApid uses SRA Study IDs (e.g., `SRP068300`) as input, not GSE IDs.**

### Why?
The raw sequencing data lives in the SRA (Sequence Read Archive), while the metadata lives in GEO.
1.  **Stability:** Querying SRA directly is robust. Converting GSE to SRP online requires web scraping or API "hops" that frequently fail on HPC clusters due to IP blocking.
2.  **Reliability:** Starting with the SRP ensures we only look for studies that actually have raw sequencing data available.

### How to find the SRP?
If you have a GSE ID (e.g., `GSE76732`), follow these steps:
1.  Go to the GEO Series page.
2.  Scroll to the very bottom and click the link labeled **SRA Run Selector**.
3.  On the new page, look at the **Common Fields** section at the top.
4.  Find the field labeled **SRA Study** to get the ID (e.g., `SRP068300`). Use this ID for your input list.

> **Note:** The table shown on the SRA Run Selector page is essentially the technical metadata this pipeline downloads. It connects the **Run** (SRR) — which we use to download FASTQs — to the **Sample** (GSM) — which we use to fetch the biological metadata.
---

## Requirements

- **Docker** (Local) or **Apptainer/Singularity** (HPC).
- **SQLite Databases** (Optional but highly recommended for speed).

### Downloading Metadata Databases

For maximum speed and reliability, download the SQLite databases locally.
It avoids internet connection issues and is significantly faster.

| Database | Download Command | Compressed | Unzipped |
| :--- | :--- | :--- | :--- |
| **SRAmetadb** | `wget https://gbnci-abcc.ncifcrf.gov/backup/SRAmetadb.sqlite.gz` | ~4 GB | **~40 GB** |
| **GEOmetadb** | `wget https://gbnci-abcc.ncifcrf.gov/geo/GEOmetadb.sqlite.gz` | ~1 GB | **~15 GB** |

**To unzip:** `gunzip *.sqlite.gz`

---

## Installation

### Method 1: HPC / Apptainer (Best for Clusters)
Pull the image directly from GitHub Container Registry.

```bash
# This builds a SIF file from the Docker image
apptainer build SRApid.sif docker://ghcr.io/theob0t/srapid:latest
```

### Method 2: Docker (Local)
```bash
docker pull ghcr.io/theob0t/srapid:latest
```

---

## Usage

Create a text file (e.g., `list.txt`) containing **SRP IDs**, one per line:
```text
SRP068300
SRP033486
```

### Option A: High Performance (With Local Databases)
**Recommended.** Uses local SQL joins. Extremely fast and stable.

```bash
# HPC / Apptainer
apptainer run --bind /gpfs:/gpfs SRApid.sif \
    --srp_list list.txt \
    --out_dir ./output \
    --sra_db /gpfs/path/to/SRAmetadb.sqlite \
    --geo_db /gpfs/path/to/GEOmetadb.sqlite \
    --cpus 10
```

### Option B: Online Mode (No Databases)
**Easiest setup.** Uses APIs (`pysradb` online mode). Good for small batches, but simpler to set up.
*Note: This skips Biological Metadata extraction if GEOmetadb is not provided.*

```bash
# HPC / Apptainer
apptainer run --bind /gpfs:/gpfs SRApid.sif \
    --srp_list list.txt \
    --out_dir ./output \
    --cpus 10
```

---

## Outputs structure
The pipeline creates the following directory structure:

```text
output/
├── technical_metadata/          # CSVs containing Run info (Library layout, Instrument, etc.)
├── biological_metadata/         # CSVs for individual GSMs (Cell line, Tissue, Age, etc.)
├── fastq/                       # One folder per SRR
│   ├── SRR123456/
│   │   ├── SRR123456_R1.fastq.gz
│   │   └── SRR123456_R2.fastq.gz
└── run_counts.csv               # Summary report of downloaded files vs total samples
```
