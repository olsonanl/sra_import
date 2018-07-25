#!/usr/bin/env python
import argparse
from string import Template
import subprocess
import csv
import glob
import json
from collections import OrderedDict
import StringIO
from lxml import etree

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

    run_metadata = []
    headers = next(reader, None)
    for line in reader:
        if line: # skip empty lines
            run_metadata.append(OrderedDict(zip(headers, line)))

    return run_metadata

def get_accession_metadata(accession_id):

    get_cmd_template = Template('curl -s \'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=docset&term=$id\'')
    get_cmd = get_cmd_template.substitute(id=accession_id)

    # call the api
    try:
        result = subprocess.check_output([get_cmd], shell=True)
    except subprocess.CalledProcessError as e:
        return_code = e.returncode

    # parse the XML results
    parser = etree.XMLParser(remove_blank_text=True)
    result_obj = StringIO.StringIO(result)
    tree = etree.parse(result_obj, parser)

    # print it out just for fun
    print(etree.tostring(tree, pretty_print=True))

    # step through the experiments
    experiments = []
    for experiment_package in tree.xpath('//EXPERIMENT_PACKAGE'):
        exp = {}
        exp['id'] = experiment_package.xpath('EXPERIMENT/@accession')[0]
        exp['study'] = experiment_package.xpath('EXPERIMENT/STUDY_REF/@accession')[0]
        exp['run_ids'] = experiment_package.xpath('RUN_SET/RUN/@accession')
        for sample in experiment_package.xpath('SAMPLE'):
            exp['sample'] = {}
            exp['sample']['id'] = sample.attrib['accession']
            sample_attrib_tags = sample.xpath('SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/TAG/text()')
            sample_attrib_vals = sample.xpath('SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/VALUE/text()')
            sample_attribs = zip(sample_attrib_tags, sample_attrib_vals)
            for sample_attrib in sample_attribs:
                exp['sample'][sample_attrib[0]] = sample_attrib[1]
        experiments.append(exp)

    return experiments

def download_fastq_files(fasterq_dump_loc, output_dir, run_ids):

    fasterq_dump_cmd_template = Template('$fasterq_dump_bin --outdir $out_dir --split-files -f $id')

    for run_id in run_ids:
        fasterq_dump_cmd = fasterq_dump_cmd_template.substitute(fasterq_dump_bin=fasterq_dump_loc, id=run_id, out_dir=output_dir)

        # call fasterq-dump
        try:
            print 'executing ' + fasterq_dump_cmd
            result = subprocess.check_output([fasterq_dump_cmd], shell=True)
        except subprocess.CalledProcessError as e:
            return_code = e.returncode

    return

def download_sra_data(fasterq_dump_loc, fastq_output_dir, accession_id, metaonly):

    # ===== 1. Get the list of runs for an accession
    run_ids = get_run_ids(accession_id)
    print 'Run IDs found:'
    print run_ids

    # ===== 2. Get the metadata for each run
    run_metadata = get_run_metadata(run_ids)
    print 'Run Metadata:'
    print json.dumps(run_metadata, indent=1)

    # ===== 3. Get the metadata for the study
    ### XXX Need to call the new method and rectify metadata... there are probably
    ### redundant calls and we can get everything we need with the docset call.  Then,
    ### we need to pack the json output.

    # ===== 4. Get the fastq files for each run
    if not metaonly:
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
    parser.add_argument('--metaonly', action='store_true', help='Skip the download of the fastq files')

    args = parser.parse_args()

    accession_id = args.id
    if accession_id.startswith(('SRX', 'SRP', 'SRR', 'DRX', 'DRP', 'DRX')):
        download_sra_data(args.bin, args.out, accession_id, args.metaonly)

        # curl -s 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=docset&term=DRP003075'
        # from xml.etree import cElementTree as ElementTree
        # root = ElementTree.fromstring(result)
        #
