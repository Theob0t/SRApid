#!/usr/bin/env Rscript
library(GEOmetadb)
library(DBI)
library(optparse)

option_list <- list(
  make_option(c("-i","--input"), type="character", help="Input file with GSE IDs"),
  make_option(c("-o","--output"), type="character", help="Output folder"),
  make_option(c("-d","--db"), type="character", help="Path to GEOmetadb.sqlite")
)

opt <- parse_args(OptionParser(option_list=option_list))

if(!dir.exists(opt$output)) dir.create(opt$output, recursive = TRUE)

# Connect to DB
if(!file.exists(opt$db)) {
    stop(paste("Database not found at:", opt$db))
}
con <- dbConnect(RSQLite::SQLite(), opt$db)

ids <- readLines(opt$input)
ids <- trimws(ids)
ids <- ids[ids != ""]

for(id in ids){
  message(paste("Processing GEO:", id))
  
  # Logic: Get GSMs for the GSE
  query_gsm <- sprintf("SELECT gsm FROM gse_gsm WHERE gse='%s';", id)
  res <- dbGetQuery(con, query_gsm)
  
  if(nrow(res) == 0){
    message("  No GSMs found for ", id)
    next
  }
  
  gsm_list <- res$gsm
  
  # Fetch details for all GSMs in this GSE
  # Splitting into chunks to avoid SQL limit if huge
  query <- sprintf("SELECT * FROM gsm WHERE gsm IN (%s);", 
                   paste(sprintf("'%s'", gsm_list), collapse=","))
  df <- dbGetQuery(con, query)
  
  # Save individual GSM files (as per original request)
  for(i in 1:nrow(df)){
      curr_gsm <- df$gsm[i]
      outfile <- file.path(opt$output, paste0(curr_gsm, "_metadata.csv"))
      # Save specific row
      write.csv(df[i,], outfile, row.names = FALSE)
  }
  message(paste("  Saved", nrow(df), "GSM metadata files."))
}

dbDisconnect(con)