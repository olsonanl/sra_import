# SRA Import Service

## Overview

The SRA Import Service enables users to seamlessly integrate sequencing data from the NCBI Sequence Read Archive (SRA) into the BV-BRC platform. This service streamlines the process of retrieving both raw sequencing reads and associated metadata, making it easier for researchers to analyze and contextualize publicly available data.  

## Service Inputs

The service accepts a single primary input:

*   **SRA Accession:**  Users can provide any of the following SRA accession types to initiate data import:
    *   **SRX (Experiment accession):** This option retrieves all runs associated with a specific experiment.
    *   **SRP (Study accession, previously known as DRP):** This option retrieves all runs associated with a given study.
    *   **SRR (Run accession):** This option retrieves data for a single sequencing run.

## Service Outputs

The service generates two primary outputs:

**1. FASTQ Files:**

*   The service downloads the raw sequencing reads in FASTQ format, maintaining the original file organization from the SRA. For paired-end sequencing data, two separate files (typically denoted with `_1` and `_2` suffixes) are generated, representing each end of the DNA fragments. Files can be downloaded in either compressed (.gz) or uncompressed format.

**2. Metadata File (for SRX and SRP accessions):**

*   For experiment (SRX) and study (SRP) accessions, the service generates a comprehensive metadata file in JSON format. This file captures relevant information about the experiment or study, including:
    *   **Sample Metadata:** Details about the biological samples, such as organism name, taxonomy, and other attributes provided in the SRA record.
    *   **Experimental Design:** Information about the experimental conditions, such as treatments, time points, and other experimental variables.
    *   **Sequencing Information:** Details about the sequencing platform, library strategy, and other technical aspects of the sequencing run. 

This metadata file is structured to conform to the requirements of downstream BV-BRC services, particularly the RNA-Seq service.

**Note:** For single run accessions (SRR), only FASTQ files are generated. Experiment-level metadata is not available for individual runs.

## Scripts and Utilities

The core functionality of the SRA Import Service is implemented in the following Python script:

| Script Name                                | Purpose                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [sra_tools.py](lib/sra_tools.py) | This script handles the retrieval of both FASTQ files and metadata from the SRA database. It employs the NCBI SRA Toolkit to download sequencing reads using the `fasterq-dump` utility and processes the retrieved metadata to generate a JSON file compatible with BV-BRC services. Key functions include: <br> * `get_run_info()`: Fetches run information from the SRA given an accession. <br> * `download_fastq()`: Downloads the FASTQ files for the specified run accession. <br> * `process_sra_metadata()`: Parses and structures SRA metadata into a JSON format suitable for downstream analysis within the BV-BRC platform. |

## See Also

*   [SRA Import Service](https://bv-brc.org/app/SRAImport) (Link to the service on the BV-BRC website, if available)

## References

*   [SRA Toolkit](https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?view=software)
*   [fasterq-dump](https://github.com/ncbi/sra-tools/wiki/HowTo:-fasterq-dump)
*   [p3diffexp](https://github.com/PATRIC3/p3diffexp)

