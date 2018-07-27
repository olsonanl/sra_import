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
import sys

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
        exp['sample_taxon'] = sample.xpath('SAMPLE_NAME/TAXON_ID/text()')[0]
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

def download_fastq_files(fastq_dump_loc, output_dir, run_ids, gzip_output=True, use_fastq_dump=False):

    if use_fastq_dump:
        # use the old fastq-dump utility
        fastq_dump_cmd_template = Template('$fastq_dump_bin/fastq-dump -I --skip-technical --split-files --read-filter pass -outdir $out_dir $id')
    else:
        # use the new fasterq-dump utility (faster, but doesn't have filtering option which results in bigger files)
        fastq_dump_cmd_template = Template('$fastq_dump_bin/fasterq-dump --outdir $out_dir --split-files -f $id')

    # for each run, download the fastq file
    for run_id in run_ids:
        fastq_dump_cmd = fastq_dump_cmd_template.substitute(fastq_dump_bin=fastq_dump_loc, id=run_id, out_dir=output_dir)

        # call fastq-dump
        try:
            print 'executing \'' + fastq_dump_cmd + '\''
            result = subprocess.check_output([fastq_dump_cmd], shell=True)
        except subprocess.CalledProcessError as e:
            return_code = e.returncode

        # gzip the output; gzip will skip anything already zipped
        if gzip_output:
            gzip_cmd = 'gzip '+output_dir+'/*.fastq'
            subprocess.call(gzip_cmd, shell=True)

    return

def download_sra_data(fastq_dump_loc, fastq_output_dir, accession_id, metaonly, compress_files, filter_reads):

    # ===== 1. Get the metadata for each run
    metadata = get_accession_metadata(accession_id)
    print 'Metadata:'
    print json.dumps(metadata, indent=1)

    # ===== 2. Get the fastq files for each run
    if not metaonly:
        download_fastq_files(fastq_dump_loc, fastq_output_dir, get_run_ids(metadata), gzip_output=compress_files, use_fastq_dump=filter_reads)
        print 'Fastq Filenames:'
        print(glob.glob(fastq_output_dir+'/*.fastq*'))

    # ===== 3. Pack it into the output JSON


    # ===== 4. Add everything to the workspace (?)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='A script to gather SRA data for a given accession id.',
                usage='usage: ./p3_sra.py -bin <path to fastq-dump> -out <fastq output directory> -id <SRA accession id (SRX, SRP, SRR)>')

    parser.add_argument('-tooldir', required=True, help='Path to the fastq-dump binary')
    parser.add_argument('-out', required=True, help='Temporary output directory for fastq files')
    parser.add_argument('-id', required=True, help='SRA accession id (SRX, SRP, SRR)')
    parser.add_argument('--metaonly', action='store_true', help='Skip the download of the fastq files')
    parser.add_argument('--gzip', action='store_true', help='Compress the fastq files after download')
    parser.add_argument('--filter', action='store_true', help='Use fastq-dump instead of fasterq-dump to leverage the read filter')

    args = parser.parse_args()

    accession_id = args.id
    acceptable_prefixes = ('SRX', 'SRP', 'SRR', 'DRX', 'DRP', 'DRR')
    if accession_id.startswith(acceptable_prefixes):
        download_sra_data(args.tooldir, args.out, accession_id, args.metaonly, args.gzip, args.filter)
    else:
        sys.exit('Accession ID must start with: ' + ', '.join(acceptable_prefixes))
