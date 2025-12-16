#!/usr/bin/env python3
import argparse
import os
import subprocess
import pandas as pd
import re
from pysradb.sradb import SRAdb
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import sys

def download_worker(srr, out_dir, limit_rows=None):
    try:
        srr_dir = os.path.join(out_dir, srr)
        os.makedirs(srr_dir, exist_ok=True)
        
        final_r1 = os.path.join(srr_dir, f"{srr}_R1.fastq.gz")
        if os.path.exists(final_r1):
            return f"{srr}: Skipped (Exists)"

        if limit_rows:
            cmd = ["fastq-dump", "--split-files", "-X", str(limit_rows), "-O", srr_dir, srr]
        else:
            cmd = ["fasterq-dump", "--split-files", "--threads", "4", "--outdir", srr_dir, "--temp", srr_dir, srr]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"pigz -f -p 4 {srr_dir}/*.fastq", shell=True, check=True)
        
        f1 = os.path.join(srr_dir, f"{srr}_1.fastq.gz")
        f2 = os.path.join(srr_dir, f"{srr}_2.fastq.gz")
        f_single = os.path.join(srr_dir, f"{srr}.fastq.gz")
        target_r1 = os.path.join(srr_dir, f"{srr}_R1.fastq.gz")
        target_r2 = os.path.join(srr_dir, f"{srr}_R2.fastq.gz")

        if os.path.exists(f1): os.rename(f1, target_r1)
        if os.path.exists(f2): os.rename(f2, target_r2)
        if os.path.exists(f_single): os.rename(f_single, target_r1)

        return f"{srr}: Success"
    except Exception as e:
        return f"{srr}: Failed ({str(e)})"

def extract_gsms_from_metadata(df):
    """
    Scans SRA metadata columns for 'GSM' patterns.
    Returns a list of unique GSM IDs found in this study.
    """
    gsm_pattern = re.compile(r"(GSM\d+)")
    
    # Columns where SRA usually hides the GEO Sample ID
    cols_to_check = ['experiment_alias', 'sample_alias', 'sample_name', 'alias', 'run_alias', 'sample_attribute']
    found_gsms = set()
    
    for col in cols_to_check:
        if col in df.columns:
            # Extractall returns a multi-index, we take level 0
            matches = df[col].dropna().astype(str).str.extractall(gsm_pattern)
            if not matches.empty:
                found_gsms.update(matches[0].tolist())
    
    return list(found_gsms)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--srp_list", required=True, help="List of SRA Study IDs (SRP...)")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--sra_db", help="Path to SRAmetadb.sqlite")
    parser.add_argument("--geo_db", help="Path to GEOmetadb.sqlite")
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--test_limit", type=int, default=None)
    args = parser.parse_args()

    bio_dir = os.path.join(args.out_dir, "biological_metadata")
    tech_dir = os.path.join(args.out_dir, "technical_metadata")
    fastq_dir = os.path.join(args.out_dir, "fastq")
    for d in [bio_dir, tech_dir, fastq_dir]:
        os.makedirs(d, exist_ok=True)

    with open(args.srp_list, 'r') as f:
        srp_ids = [x.strip() for x in f if x.strip()]

    # Setup SRA Access
    db = None
    db_online = None
    if args.sra_db and os.path.exists(args.sra_db):
        print(f"Using Local DB: {args.sra_db}")
        db = SRAdb(args.sra_db)
    else:
        print("Using Online Mode (pysradb)")
        from pysradb import SRAweb
        db_online = SRAweb()

    srr_download_list = []
    all_detected_gsms = []

    # --- Step 1: Technical Metadata (SRA) & GSM Discovery ---
    print(f"\n[Step 1] Querying SRA for {len(srp_ids)} studies...")
    
    for srp in tqdm(srp_ids):
        df = None
        try:
            if db:
                df = db.sra_metadata(srp)
            else:
                df = db_online.sra_metadata(srp)
        except Exception as e:
            print(f"  Error fetching {srp}: {e}")

        if df is not None and not df.empty:
            # Save Tech Metadata
            out_name = os.path.join(tech_dir, f"{srp}_metadata.csv")
            df.to_csv(out_name, index=False)
            
            # Collect SRRs
            if 'run_accession' in df.columns:
                srr_download_list.extend(df['run_accession'].dropna().tolist())
            
            # Discover GSM IDs
            gsms = extract_gsms_from_metadata(df)
            if gsms:
                all_detected_gsms.extend(gsms)
                print(f"  {srp} -> Found {len(gsms)} GSMs (e.g., {gsms[0]})")
            else:
                print(f"  {srp} -> No GSMs found in metadata (Biological metadata may be missing)")
        else:
            print(f"  WARNING: No data found for {srp}")

    # --- Step 2: Biological Metadata (GEO) ---
    # We pass the list of specific GSMs to R
    unique_gsms = list(set(all_detected_gsms))
    
    if unique_gsms and args.geo_db and os.path.exists(args.geo_db):
        print(f"\n[Step 2] Extracting Biological Metadata for {len(unique_gsms)} GSMs...")
        temp_gsm_file = os.path.join(args.out_dir, "discovered_GSMs.txt")
        with open(temp_gsm_file, 'w') as f:
            for g in unique_gsms:
                f.write(f"{g}\n")
        
        subprocess.run(["Rscript", "/usr/local/src/gsm2metadata.R", 
                        "--input", temp_gsm_file, 
                        "--output", bio_dir, 
                        "--db", args.geo_db], check=True)
    else:
        if not unique_gsms:
            print("\n[Step 2] Skipping GEO (No GSMs found in SRA metadata)")
        else:
            print("\n[Step 2] Skipping GEO (DB missing)")

    # --- Step 3: Download FASTQs ---
    unique_srrs = list(set(srr_download_list))
    if not unique_srrs:
        print("No SRRs found.")
        if args.test_limit: sys.exit(1)
        return

    if args.test_limit:
        print(f"TEST MODE: Limit 1 SRR, {args.test_limit} rows")
        unique_srrs = [unique_srrs[0]]

    print(f"\n[Step 3] Downloading {len(unique_srrs)} runs...")
    with ProcessPoolExecutor(max_workers=args.cpus) as executor:
        futures = {executor.submit(download_worker, srr, fastq_dir, args.test_limit): srr for srr in unique_srrs}
        for future in tqdm(as_completed(futures), total=len(unique_srrs)):
            pass 

    # --- Step 4: Validate ---
    subprocess.run(["python3", "/usr/local/src/validate_run.py", 
                    "--input_list", args.srp_list, 
                    "--base_dir", args.out_dir], check=False)

if __name__ == "__main__":
    main()