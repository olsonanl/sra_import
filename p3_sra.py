#!/usr/bin/env
import argparse
from string import Template
import subprocess
import csv
import glob

def get_run_ids(accession_id):
    # the -s is for curl's silent mode (omit the headers)
    get_runs_cmd_template = Template('curl -s \'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=$id\' | grep $id | cut -f1 -d","')
    get_runs_cmd = get_runs_cmd_template.substitute(id=accession_id)

    # call the api
    try:
        result = subprocess.check_output([get_runs_cmd], shell=True)
    except subprocess.CalledProcessError as e:
        return_code = e.returncode

    # get the run ids as a list
    run_ids = result.splitlines()

    return run_ids

def get_run_metadata(run_ids):

    # format the run ids as (SRR_1)OR(SRR_2)OR ...
    str_buf = []
    for run_id in run_ids:
        str_buf.append('('+run_id+')')
    run_ids_query_str = 'OR'.join(str_buf)

    get_run_metadata_cmd_template = Template('curl -s \'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term=$ids\'')
    get_run_metadata_cmd = get_run_metadata_cmd_template.substitute(ids=run_ids_query_str)

    # call the api
    try:
        result = subprocess.check_output([get_run_metadata_cmd], shell=True)
    except subprocess.CalledProcessError as e:
        return_code = e.returncode

    # get the results as a csv and then convert to list of dictionaries
    reader = csv.reader(result.splitlines())

    metadata = []
    headers = next(reader, None)
    for line in reader:
        if line: # skip empty lines
            metadata.append(dict(zip(headers, line)))

    return metadata

def download_fastq_files(fasterq_dump_loc, output_dir, run_ids):

    fasterq_dump_cmd_template = Template('$fasterq_dump_bin --outdir $out_dir --split-files -f $id')

    for run_id in run_ids:
        fasterq_dump_cmd = fasterq_dump_cmd_template.substitute(fasterq_dump_bin=fasterq_dump_loc, id=run_id, out_dir=output_dir)

        # call fasterq-dump
        try:
            result = subprocess.check_output([fasterq_dump_cmd], shell=True)
        except subprocess.CalledProcessError as e:
            return_code = e.returncode

    return

def download_sra_data(fasterq_dump_loc, fastq_output_dir, accession_id):

    # ===== 1. Get the list of runs for an accession
    run_ids = get_run_ids(accession_id)
    print 'Run IDs found:'
    print run_ids

    # ===== 2. Get the metadata for each run
    metadata = get_run_metadata(run_ids)
    print 'Run Metadata:'
    print metadata

    # ===== 3. Get the fastq files for each run
    download_fastq_files(fasterq_dump_loc, fastq_output_dir, run_ids)

    print 'Fastq Filenames:'
    print(glob.glob(fastq_output_dir+'/*.fastq'))

    # we have files and metadata... now what?

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='A script to gather SRA data for a given accession id.',
                usage='usage: ./p3_sra.py -bin <path to fasterq-dump> -out <fastq output directory> -id <SRA accession id (SRX, SRP, SRR)>')

    parser.add_argument('-bin', required=True, help='Path to the fasterq-dump binary')
    parser.add_argument('-out', required=True, help='Temporary output directory for fastq files')
    parser.add_argument('-id', required=True, help='SRA accession id (SRX, SRP, SRR)')

    args = parser.parse_args()

    accession_id = args.id
    if accession_id.startswith('SRX') or accession_id.startswith('SRP') or accession_id.startswith('SRR'):
        download_sra_data(args.bin, args.out, accession_id)
