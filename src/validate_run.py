#!/usr/bin/env python3
import pandas as pd
import os
import glob
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gse_list", required=True)
    parser.add_argument("--base_dir", required=True)
    args = parser.parse_args()

    bio_meta_dir = os.path.join(args.base_dir, 'biological_metadata/metadata')
    tech_meta_dir = os.path.join(args.base_dir, 'technical_metadata')
    fastq_base_dir = os.path.join(args.base_dir, 'fastq')
    out_csv = os.path.join(args.base_dir, 'GSE_run_counts.csv')

    with open(args.gse_list, 'r') as f:
        target_gse_list = [x.strip() for x in f if x.strip()]

    counts_data = []

    print(f"Validating {len(target_gse_list)} GSEs...")

    for gse_id in target_gse_list:
        n_samples = 0
        n_fastq = 0
        
        # 1. Tech Metadata
        tech_file = os.path.join(tech_meta_dir, f"{gse_id}_metadata.csv")
        
        if os.path.exists(tech_file):
            try:
                # We saved as CSV in pipeline.py
                tech_df = pd.read_csv(tech_file)
                if 'run_accession' in tech_df.columns:
                    srr_list = tech_df['run_accession'].dropna().unique()
                    n_samples = len(srr_list)
                    
                    for srr in srr_list:
                        srr = str(srr).strip()
                        # Check /fastq/SRR/SRR_R1.fastq.gz
                        fq_path = os.path.join(fastq_base_dir, srr, f"{srr}_R1.fastq.gz")
                        if os.path.exists(fq_path):
                            n_fastq += 1
            except Exception as e:
                print(f"Err {gse_id}: {e}")
        
        # 2. Bio Metadata (Just checking existence implies success of R script)
        # Count how many GSM files exist for this GSE?
        # This is harder without the GSM list, but we can glob
        # Or just rely on tech metadata match.
        # Simple check:
        counts_data.append({
            'GSE': gse_id,
            'n_samples_tech': n_samples,
            'n_fastq_downloaded': n_fastq
        })

    df = pd.DataFrame(counts_data)
    df.to_csv(out_csv, index=False)
    print(f"Validation saved to {out_csv}")

if __name__ == "__main__":
    main()