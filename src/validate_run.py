#!/usr/bin/env python3
import pandas as pd
import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_list", required=True, help="List of SRP IDs")
    parser.add_argument("--base_dir", required=True, help="Output directory containing metadata/fastq folders")
    args = parser.parse_args()

    # Flattened structure as per your request
    tech_meta_dir = os.path.join(args.base_dir, 'technical_metadata')
    bio_meta_dir = os.path.join(args.base_dir, 'biological_metadata') 
    fastq_base_dir = os.path.join(args.base_dir, 'fastq')
    out_csv = os.path.join(args.base_dir, 'run_counts.csv')

    with open(args.input_list, 'r') as f:
        target_list = [x.strip() for x in f if x.strip()]

    counts_data = []

    print(f"Validating {len(target_list)} IDs...")

    for ident in target_list:
        n_samples_tech = 0
        n_fastq_downloaded = 0
        n_bio_expected = 0
        n_bio_found = 0
        
        # 1. Load Technical Metadata
        tech_file = os.path.join(tech_meta_dir, f"{ident}_metadata.csv")
        
        if os.path.exists(tech_file):
            try:
                tech_df = pd.read_csv(tech_file)
                
                # --- Count Technical Samples (SRRs) ---
                if 'run_accession' in tech_df.columns:
                    srr_list = tech_df['run_accession'].dropna().unique()
                    n_samples_tech = len(srr_list)
                    
                    # Check for FASTQs
                    for srr in srr_list:
                        srr = str(srr).strip()
                        # Check for R1 file
                        fq_path = os.path.join(fastq_base_dir, srr, f"{srr}_R1.fastq.gz")
                        if os.path.exists(fq_path):
                            n_fastq_downloaded += 1

                # --- Count Biological Samples (GSMs) ---
                # We attempt to find GSM IDs hidden in the SRA metadata
                potential_gsms = set()
                # Common columns where SRA stores the GEO Name
                cols_to_check = ['experiment_alias', 'sample_alias', 'sample_name', 'alias']
                
                for col in cols_to_check:
                    if col in tech_df.columns:
                        # Extract values starting with 'GSM'
                        matches = tech_df[col].dropna().astype(str)
                        gsm_matches = matches[matches.str.startswith('GSM')]
                        potential_gsms.update(gsm_matches.tolist())
                
                n_bio_expected = len(potential_gsms)
                
                # Check if the GSM metadata file exists
                for gsm in potential_gsms:
                    bio_file = os.path.join(bio_meta_dir, f"{gsm}_metadata.csv")
                    if os.path.exists(bio_file):
                        n_bio_found += 1
                        
            except Exception as e:
                print(f"Error reading/parsing {ident}: {e}")
        else:
            print(f"Warning: Technical metadata missing for {ident}")
        
        counts_data.append({
            'SRP_ID': ident,
            'n_tech_samples': n_samples_tech,       # Rows in SRA
            'n_fastq_found': n_fastq_downloaded,    # Actual .gz files
            'n_bio_expected': n_bio_expected,       # GSMs mentioned in SRA
            'n_bio_found': n_bio_found              # GSM CSVs actually downloaded
        })

    # Save Report
    df = pd.DataFrame(counts_data)
    df.to_csv(out_csv, index=False)
    print(f"Validation saved to {out_csv}")
    
    # Simple summary to stdout
    print("\nSummary:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()