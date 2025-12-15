#!/usr/bin/env python3
import argparse
import os
import subprocess
import pandas as pd
from pysradb.sradb import SRAdb
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import sys
import shutil

# --- helper function for downloading ---
def download_worker(srr, out_dir, limit_rows=None):
    """
    Downloads, renames, and zips files for a single SRR.
    """
    try:
        srr_dir = os.path.join(out_dir, srr)
        os.makedirs(srr_dir, exist_ok=True)
        
        # Check if already done
        final_r1 = os.path.join(srr_dir, f"{srr}_R1.fastq.gz")
        if os.path.exists(final_r1):
            return f"{srr}: Skipped (Exists)"

        # Command construction
        # Note: fasterq-dump does not support -X (limit rows), fastq-dump does.
        if limit_rows:
            cmd = [
                "fastq-dump", "--split-files", 
                "-X", str(limit_rows), 
                "-O", srr_dir, srr
            ]
        else:
            # Use 4 threads per dump, temp dir in current folder to avoid /tmp space issues on HPC
            cmd = [
                "fasterq-dump", "--split-files", 
                "--threads", "4", 
                "--outdir", srr_dir, 
                "--temp", srr_dir, 
                srr
            ]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Renaming Logic
        # fasterq-dump produces: SRR_1.fastq, SRR_2.fastq OR SRR.fastq
        files = os.listdir(srr_dir)
        
        # Pigz compression
        subprocess.run(f"pigz -p 4 {srr_dir}/*.fastq", shell=True, check=True)
        
        # Rename logic on .gz files
        f1 = os.path.join(srr_dir, f"{srr}_1.fastq.gz")
        f2 = os.path.join(srr_dir, f"{srr}_2.fastq.gz")
        f_single = os.path.join(srr_dir, f"{srr}.fastq.gz")
        
        target_r1 = os.path.join(srr_dir, f"{srr}_R1.fastq.gz")
        target_r2 = os.path.join(srr_dir, f"{srr}_R2.fastq.gz")

        if os.path.exists(f1):
            os.rename(f1, target_r1)
        if os.path.exists(f2):
            os.rename(f2, target_r2)
        if os.path.exists(f_single):
            os.rename(f_single, target_r1) # Treat single as R1

        return f"{srr}: Success"

    except Exception as e:
        return f"{srr}: Failed ({str(e)})"

# --- Main Pipeline ---
def main():
    parser = argparse.ArgumentParser(description="Full SRA/GEO Download Pipeline")
    parser.add_argument("--gse_list", required=True, help="Path to text file with GSE IDs")
    parser.add_argument("--out_dir", required=True, help="Base output directory")
    parser.add_argument("--sra_db", help="Path to SRAmetadb.sqlite")
    parser.add_argument("--geo_db", help="Path to GEOmetadb.sqlite")
    parser.add_argument("--cpus", type=int, default=4, help="Number of parallel downloads")
    parser.add_argument("--test_limit", type=int, default=None, help="Download only N rows (CI test)")
    
    args = parser.parse_args()

    # Directories
    bio_dir = os.path.join(args.out_dir, "biological_metadata/metadata")
    tech_dir = os.path.join(args.out_dir, "technical_metadata")
    fastq_dir = os.path.join(args.out_dir, "fastq")
    
    os.makedirs(bio_dir, exist_ok=True)
    os.makedirs(tech_dir, exist_ok=True)
    os.makedirs(fastq_dir, exist_ok=True)

    # Load IDs
    with open(args.gse_list, 'r') as f:
        gse_ids = [x.strip() for x in f if x.strip()]

    print(f"=== Starting Pipeline for {len(gse_ids)} GSEs ===")

    # 1. Biological Metadata (R Script)
    if args.geo_db and os.path.exists(args.geo_db):
        print("\n[Step 1] Extracting Biological Metadata (GEO)...")
        cmd = [
            "Rscript", "/usr/local/src/gsm2metadata.R",
            "--input", args.gse_list,
            "--output", bio_dir,
            "--db", args.geo_db
        ]
        subprocess.run(cmd, check=True)
    else:
        print("\n[Step 1] Skipping GEO metadata (DB not provided or missing)")

    # 2. Technical Metadata (Python/pysradb)
    print("\n[Step 2] Extracting Technical Metadata (SRA)...")
    
    srr_download_list = []
    
    # Initialize DB if local
    db = None
    if args.sra_db and os.path.exists(args.sra_db):
        try:
            db = SRAdb(args.sra_db)
        except Exception as e:
            print(f"Failed to load SRA DB: {e}")

    for gse in tqdm(gse_ids):
        try:
            df = pd.DataFrame()
            if db:
                # Local DB query
                # Convert GSE to SRP implicitly via metadata query if possible, 
                # or use gse_to_srp then sra_metadata
                try:
                    df = db.sra_metadata(gse)
                except:
                    # Fallback: try converting GSE -> SRP
                    srp_df = db.gse_to_srp([gse])
                    if not srp_df.empty:
                        srp = srp_df.iloc[0]['study_accession']
                        df = db.sra_metadata(srp)
            else:
                # Online mode fallback (slower but good for CI)
                from pysradb import SRAweb
                sradb_online = SRAweb()
                df = sradb_online.sra_metadata(gse)

            if not df.empty:
                out_name = os.path.join(tech_dir, f"{gse}_metadata.csv")
                # Ensure tab separated or csv as preferred. User code used comma in one place, tab in other.
                # Let's standardize on CSV for this pipeline
                df.to_csv(out_name, index=False)
                
                if 'run_accession' in df.columns:
                    srr_list = df['run_accession'].dropna().tolist()
                    srr_download_list.extend(srr_list)
        except Exception as e:
            print(f"Error processing {gse}: {e}")

    # 3. Download FASTQs
    unique_srrs = list(set(srr_download_list))
    print(f"\n[Step 3] Downloading {len(unique_srrs)} FASTQ runs...")
    print(f"Threads: {args.cpus} workers")

    # Limit for CI test
    if args.test_limit and len(unique_srrs) > 0:
        print(f"TEST MODE: Processing only 1 SRR with {args.test_limit} rows.")
        unique_srrs = [unique_srrs[0]]

    with ProcessPoolExecutor(max_workers=args.cpus) as executor:
        futures = {
            executor.submit(download_worker, srr, fastq_dir, args.test_limit): srr 
            for srr in unique_srrs
        }
        
        for future in tqdm(as_completed(futures), total=len(unique_srrs)):
            res = future.result()
            # Optional: log failures to a file

    # 4. Validation
    print("\n[Step 4] Validating...")
    validate_cmd = [
        "python3", "/usr/local/src/validate_run.py",
        "--gse_list", args.gse_list,
        "--base_dir", args.out_dir
    ]
    subprocess.run(validate_cmd)

    print("\nPipeline Complete.")

if __name__ == "__main__":
    main()