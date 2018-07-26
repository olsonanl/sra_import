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
    #print(etree.tostring(tree, pretty_print=True))

    # step through the experiments
    exp_meta = []
    for experiment_package in tree.xpath('//EXPERIMENT_PACKAGE'):
        exp = {}
        exp['exp_id'] = experiment_package.xpath('EXPERIMENT/@accession')[0]
        exp['study_id'] = experiment_package.xpath('EXPERIMENT/STUDY_REF/@accession')[0]

        for db in experiment_package.xpath('STUDY//XREF_LINK/DB/text()'):
            exp['study_'+db+'_ids'] = experiment_package.xpath('STUDY//XREF_LINK/ID/text()')

        exp['run_ids'] = experiment_package.xpath('RUN_SET/RUN/@accession')
        exp['library_name'] = experiment_package.xpath('EXPERIMENT//LIBRARY_NAME/text()')[0]
        exp['library_strategy'] = experiment_package.xpath('EXPERIMENT//LIBRARY_STRATEGY/text()')[0]

        # just assume one sample
        sample = experiment_package.xpath('SAMPLE')[0]
        exp['sample_id'] = sample.attrib['accession']
        exp['sample_description'] = sample.xpath('DESCRIPTION/text()')[0]
        exp['sample_organism'] = sample.xpath('SAMPLE_NAME/SCIENTIFIC_NAME/text()')[0]
        sample_attrib_tags = sample.xpath('SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/TAG/text()')
        sample_attrib_vals = sample.xpath('SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/VALUE/text()')
        sample_attribs = zip(sample_attrib_tags, sample_attrib_vals)
        for sample_attrib in sample_attribs:
            # prepend sample_ for each key related to the sample (unless it's already there)
            if sample_attrib[0].startswith('sample_'):
                    key = sample_attrib[0]
            else:
                key = 'sample_' + sample_attrib[0]
            exp[key] = sample_attrib[1]
        exp_meta.append(exp)

    # create a new run-centric metadata dict
    run_meta = []

    # for each run id in each experiment, create a new record
    for exp in exp_meta:
        for run_id in exp['run_ids']:
            run = {}
            run['run_id'] = run_id
            for k in exp:
                if k != 'run_ids':
                    run[k] = exp[k]
            run_meta.append(run)

    return run_meta

def get_run_ids(run_meta):
    run_ids = []
    for run in run_meta:
        run_ids.append(run['run_id'])
    return run_ids

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

    # ===== 1. Get the metadata for each run
    metadata = get_accession_metadata(accession_id)
    print 'Metadata:'
    print json.dumps(metadata, indent=1)

    # ===== 2. Pack it into the output JSON
    

    # ===== 3. Get the fastq files for each run
    if not metaonly:
        download_fastq_files(fasterq_dump_loc, fastq_output_dir, get_run_ids(metadata))
        print 'Fastq Filenames:'
        print(glob.glob(fastq_output_dir+'/*.fastq'))

    # ===== 4. Add everything to the workspace (?)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='A script to gather SRA data for a given accession id.',
                usage='usage: ./p3_sra.py -bin <path to fasterq-dump> -out <fastq output directory> -id <SRA accession id (SRX, SRP, SRR)>')

    parser.add_argument('-bin', required=True, help='Path to the fasterq-dump binary')
    parser.add_argument('-out', required=True, help='Temporary output directory for fastq files')
    parser.add_argument('-id', required=True, help='SRA accession id (SRX, SRP, SRR)')
    parser.add_argument('--metaonly', action='store_true', help='Skip the download of the fastq files')

    args = parser.parse_args()

    accession_id = args.id
    if accession_id.startswith(('SRX', 'SRP', 'SRR', 'DRX', 'DRP', 'DRR')):
        download_sra_data(args.bin, args.out, accession_id, args.metaonly)

        # curl -s 'https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=docset&term=DRP003075'
        # from xml.etree import cElementTree as ElementTree
        # root = ElementTree.fromstring(result)
        #
