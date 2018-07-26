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

0. A project (SRP) has one or more samples. However, projects are in the table called study.

  A sample (SRS) has one or more experiments (SRX).

  An experiment has one or more runs (SRR).

1. [SRA toolkit](https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?view=software) Use fastq-dump, set flag for split files.

2. "Runs" are each 2 paired fastq files.

3. SRA metadata.  [From EdwardsLab](https://edwards.sdsu.edu/research/sra-metadata/). From Alan: [SRA metadata SQL lite file](https://s3.amazonaws.com/starbuck1/sradb/SRAmetadb.sqlite.gz)
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
  ```
  select run_accession, experiment_accession, study_accession, description, sample_attribute from sra where study_accession = 'DRP003075';
  ```

6. [FangFang's method for getting files](https://github.com/TheSEED/app_service/blob/master/scripts/App-GenomeAssembly.pl#L245-L268)

7. [Bruce's method for getting files](https://github.com/SEEDtk/kernel/blob/master/scripts/p3-download-samples.pl)

   `Q`: Bruce, are you currently pulling any of the seedtk/kernel stuff into CVS? I see SRAlib.pm is already there; if we can add p3-dowload-samples then it’ll be available to the backend services.

   `A`: The p3 scripts that are in kernel generally won’t work without additional software. In the case of this particular script, it’s the NCBI’s SRA toolkit, a marauding monster that steals copious amounts of disk space under the covers. I can put it in CVS, but the code that hunts for the location of the SRA toolkit is SEEDtk-dependent. We would need to come up with an alternative strategy.

9. `Q`: How should we handle fastq-dump binary?  
   `A`: Need to ask Bob to install.

10. There is now a  [fasterq-dump](https://github.com/ncbi/sra-tools/wiki/HowTo:-fasterq-dump). From thier wiki:

   _With release 2.9.1 of sra-tools we have finally made available the tool fasterq-dump, a replacement for the much older fastq-dump tool. As its name implies, it runs faster, and is better suited for large-scale conversion of SRA objects into FASTQ files that are common on sites with enough disk space for temporary files. fasterq-dump is multi-threaded and performs bulk joins in a way that improves performance as compared to fastq-dump, which performs joins on a per-record basis (and is single-threaded). fastq-dump is still supported as it handles more corner cases than fasterq-dump, but it is likely to be deprecated in the future._

11. [A sample Perl wrapper for a PATRIC service](https://github.com/TheSEED/app_service/blob/master/scripts/App-TnSeq.pl) and [the Python thing it wraps](https://github.com/PATRIC3/p3_tnseq/blob/master/scripts/p3_tnseq.py)

12. Old command:
   ```
   fastq-dump -outdir tmp --skip-technical --readids --read-filter pass --dumpbase --split-3 --clip
   ```

   * split-3 is the default now
   * skip-technical is the default now
   * there is no readids (append read id after spot id as
 'accession.spot.readid' on defline)
   * there is no read-filter (Filters Applied to spots when --split-spot is not set, otherwise - to individual reads; Split into files by READ_FILTER value pass|reject|criteria|redacted)
   * there is no dumpbase (formats sequence using base space, which was default for all except SOLiD)
   * there is no clip (Full Spot Filters Applied to the full spot independently - apply left and right clips)

   New command:
   ```
   fasterq-dump --outdir tmp --split-files
   ```

13. fasterq-dump doesn't have an easy "pass" read-filter like fastq-dump does.  It does have a "filter by bases" option.  

14. Check in on whether there's caching or temp files that will need to be cleaned up.  I know it cleans up the temp files (and we can control where they are), but is there any kind of additional caching?

15. Maulik:
  * Find all the samples and read runs using SRA Study Accession: [1](https://www.ncbi.nlm.nih.gov/Traces/study/?acc=SRP039561)  [2](https://www.ncbi.nlm.nih.gov/Traces/study/?acc=SRP100071)
  * Use the run table available from the links above to pull sample names
and other basic metadata (i.e. organism name, taxonomy, etc) and present it
to user in a way that can be used to prepare labels for job input.
  * Use the run list to retrieve all the run accessions and corresponding read files from SRA:
   ```
   fastq-dump -I --skip-technical --split-files --gzip SRR5660159
   ```

16. We can get the runs for a study with (works with SRP, SRX, and SRR):
   ```
   curl 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=SRP039561' | grep SRP039561 | cut -f1 -d","

   curl 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=SRX2568064' | grep 'SRX2568064' | cut -f1 -d","

   curl 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=SRR1185914' | grep 'SRR1185914' | cut -f1 -d","

   curl 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=(SRR1185914)OR(SRR1185915)'
   ```
   Fields returned:
   * Run
   * ReleaseDate
   * LoadDate
   * spots
   * bases
   * spots_with_mates
   * avgLength
   * size_MB
   * AssemblyName
   * download_path
   * Experiment
   * LibraryName
   * LibraryStrategy
   * LibrarySelection
   * LibrarySource
   * LibraryLayout
   * InsertSize
   * InsertDev
   * Platform
   * Model
   * SRAStudy
   * BioProject
   * Study_Pubmed_id
   * ProjectID
   * Sample
   * BioSample
   * SampleType
   * TaxID
   * ScientificName
   * SampleName
   * g1k_pop_code
   * source
   * g1k_analysis_group
   * Subject_ID
   * Sex
   * Disease
   * Tumor
   * Affection_Status
   * Analyte_Type
   * Histological_Type
   * Body_Site
   * CenterName
   * Submission
   * dbgap_study_accession
   * Consent
   * RunHash
   * ReadHash

17. Want to create a similar JSON file to use as input to RNA-Seq:
  ```
  {
      "output_path": "/anwarren@patricbrc.org/home/test",
      "output_file": "easter",
      "recipe": "RNA-Rocket",
      "reference_genome_id": "205918.60",
      "contrasts": [
          [
              1,
              2
          ]
      ],
      "paired_end_libs": [
          {
              "condition": 1,
              "read1": "/anwarren@patricbrc.org/home/reads/bau_sim_R1.fq.gz",
              "read2": "/anwarren@patricbrc.org/home/MSK/bau_sim_R2.fq"
          },
          {
              "condition": 2,
              "read1": "/anwarren@patricbrc.org/home/MSK/bau_sim_R2.fq",
              "read2": "/anwarren@patricbrc.org/home/reads/bau_sim_R1.fq.gz"
          }
      ],
      "experimental_conditions": [
          "hey",
          "hey1"
      ],
      "single_end_libs": [
          {
              "condition": 2,
              "read": "/anwarren@patricbrc.org/home/rnaseq_test/MHB_R1.fq.gz"
          }
      ]
  }
  ```

  18. We can get a lot more metadata from the 'docset' call:
     ```
     curl -s 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=docset&term=DRR021383'
     ```
