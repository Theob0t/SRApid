#!/usr/bin/env Rscript
library(GEOmetadb)
library(DBI)
library(optparse)

option_list <- list(
  make_option(c("-i","--input"), type="character", help="Input file with GSM IDs (one per line)"),
  make_option(c("-o","--output"), type="character", help="Output folder"),
  make_option(c("-d","--db"), type="character", help="Path to GEOmetadb.sqlite")
)

opt <- parse_args(OptionParser(option_list=option_list))

if(!dir.exists(opt$output)) dir.create(opt$output, recursive = TRUE)

if(!file.exists(opt$db)) {
    stop(paste("Database not found at:", opt$db))
}

con <- dbConnect(RSQLite::SQLite(), opt$db)

ids <- readLines(opt$input)
ids <- trimws(ids)
ids <- ids[ids != "" & grepl("^GSM", ids)] # Filter only valid GSMs

message(paste("Processing", length(ids), "unique GSM IDs..."))

# Function to process chunks (SQLite has limit on number of variables in IN clause)
chunk_size <- 500
split_ids <- split(ids, ceiling(seq_along(ids)/chunk_size))

for(chunk in split_ids) {
    # Create SQL list string: 'GSM1','GSM2','GSM3'
    sql_list <- paste(sprintf("'%s'", chunk), collapse=",")
    
    query <- sprintf("SELECT * FROM gsm WHERE gsm IN (%s);", sql_list)
    df <- dbGetQuery(con, query)
    
    if(nrow(df) > 0) {
        # Iterate through results and save individual files
        for(i in 1:nrow(df)){
            curr_gsm <- df$gsm[i]
            outfile <- file.path(opt$output, paste0(curr_gsm, "_metadata.csv"))
            write.csv(df[i,], outfile, row.names = FALSE)
        }
    }
}

message(paste("Saved metadata files to", opt$output))
dbDisconnect(con)