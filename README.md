# SRApid Pipeline

A Dockerized pipeline to download technical metadata (SRA), biological metadata (GEO), and FASTQ files for a list of GSE IDs.

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

