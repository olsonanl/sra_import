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
