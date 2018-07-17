# SRA Import
```
Inputs:
#1 SRA accession SRX, SRP, SRR

Outputs:
#1 Fastq files (2 files for paired samples)
#2 Metadata conversion of SRA data to PATRIC. Conforms to https://github.com/PATRIC3/p3diffexp/tree/master/test

This program will:
#1 Use the given SRA accession and NCBI fastq dump to download fastq files and associated metadata

For SRR accession only fastq files will be created (no experiment level metadata file)
```

# Notes

1. [SRA toolkit](https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?view=software)
   Use fastq-dump, set flag for split files and flag for <special machine>.

2. "Runs" are each 2 paired fastq files.

3. [SRA metadata SQL lite file](https://s3.amazonaws.com/starbuck1/sradb/SRAmetadb.sqlite.gz)
   There is one table, named sra, which flattens out data from other tables into one giant row per 'run_accession' (eg. SRRnnnnn)

   Key fields are:
  * run_accession: the id of the specific fastq file (or 2 paired-end files)
  * experiment_accession: possibly a grouping variable for multiple runs
  * study_accession: definitely a grouping variable for multiple runs
  * library_strategy: kind of data: this is "RNA-Seq" for gene expression studies
  * description: this is sometimes useful to distinguish treatments for gene expression experiments
  * sample_attribute: this has multiple pieces of information about the sample, eg treatment


4. Sample study DRP003075 with helpful views:
  * [https://trace.ncbi.nlm.nih.gov/Traces/study/?acc=DRP003075](https://trace.ncbi.nlm.nih.gov/Traces/study/?acc=DRP003075)
  * [https://www.ncbi.nlm.nih.gov/sra/DRX019545[accn]](https://www.ncbi.nlm.nih.gov/sra/DRX019545[accn])

5. Sample SQL grabbing similar metadata fields for all runs for the study:
```select run_accession, experiment_accession, study_accession, description, sample_attribute from sra where study_accession = 'DRP003075';```

6. [FangFang's method for getting files](https://github.com/TheSEED/app_service/blob/master/scripts/App-GenomeAssembly.pl#L245-L252)

7. [Bruce's method for getting files](https://github.com/SEEDtk/kernel/blob/master/scripts/p3-download-samples.pl)

8. 
   `Q`: Bruce, are you currently pulling any of the seedtk/kernel stuff into CVS? I see SRAlib.pm is already there; if we can add p3-dowload-samples then it’ll be available to the backend services.

   `A`: The p3 scripts that are in kernel generally won’t work without additional software. In the case of this particular script, it’s the NCBI’s SRA toolkit, a marauding monster that steals copious amounts of disk space under the covers. I can put it in CVS, but the code that hunts for the location of the SRA toolkit is SEEDtk-dependent. We would need to come up with an alternative strategy.
