from string import Template
import subprocess
import csv
import glob
import json
import os
from collections import OrderedDict
import StringIO
from lxml import etree
import sys

import shutil
import urllib2

def safe_read(element, xpath, index=None, xpath_fallback=None):

    # the logic here is basically, try one tag, if it's not there, return an
    # alternate tag. for either case, if there's a specific element you want
    # (like 0), just return that instead of the list.

    # also, I haven't tested to be sure this is really all that safe.  it's just
    # safer than the way I was doing it.

    val = element.xpath(xpath)
    if val:
        if index is not None:
            return val[index]
        else:
            return val
    elif xpath_fallback is not None:
        return safe_read(element, xpath_fallback, index)
    else:
        return ''


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
        exp['exp_id'] = safe_read(experiment_package, 'EXPERIMENT/@accession', index=0)
        exp['study_id'] = safe_read(experiment_package, 'EXPERIMENT/STUDY_REF/@accession', index=0)

        for db in experiment_package.xpath('STUDY//XREF_LINK/DB/text()'):
            exp['study_'+db+'_ids'] = experiment_package.xpath('STUDY//XREF_LINK/ID/text()')

        exp['runs'] = []
        for run in experiment_package.xpath('RUN_SET/RUN'):
            rdata = {}
            rdata['run_id'] = safe_read(run, '@accession')[0]
            rdata['accession'] = rdata['run_id']
            rdata['total_bases'] = safe_read(run, '@total_bases')[0]
            rdata['size'] = safe_read(run, '@size')[0]
            print(rdata)
            exp['runs'].append(rdata)

        exp['library_name'] = safe_read(experiment_package, 'EXPERIMENT//LIBRARY_NAME/text()', index=0)
        exp['library_strategy'] = safe_read(experiment_package, 'EXPERIMENT//LIBRARY_STRATEGY/text()', index=0)
        #this might be unreliable. use the existence of paired file
        exp['library_layout'] = "PAIRED" if safe_read(experiment_package, 'EXPERIMENT//LIBRARY_LAYOUT/PAIRED', index=0) != "" else "SINGLE" 

        # just assume one sample
        sample = safe_read(experiment_package, 'SAMPLE', index=0)
        exp['sample_id'] = sample.attrib['accession']
        exp['sample_title'] = safe_read(sample, 'TITLE/text()', index=0)
        exp['sample_description'] = safe_read(sample, 'DESCRIPTION/text()', index=0)
        exp['sample_organism'] = safe_read(sample, 'SAMPLE_NAME/SCIENTIFIC_NAME/text()', index=0)
        exp['sample_taxon'] = safe_read(sample, 'SAMPLE_NAME/TAXON_ID/text()', index=0)
        sample_attrib_tags = safe_read(sample, 'SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/TAG/text()')
        sample_attrib_vals = safe_read(sample, 'SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE/VALUE/text()')
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
        for rdata in exp['runs']:
            run = {}
            for k in rdata:
                run[k] = rdata[k]
            for k in exp:
                if k != 'runs':
                    run[k] = exp[k]
            run_meta.append(run)

    return run_meta

def get_runinfo(run_accession):
    """ take sra run accession (like SRR123456)
    return dictionary with keys like: spots,bases,spots_with_mates,avgLength,size_MB,AssemblyName,download_path.....
    """
    runinfo_url = "https://trace.ncbi.nlm.nih.gov/Traces/sra/sra.cgi?save=efetch&db=sra&rettype=runinfo&term="+run_accession
    r = urllib2.urlopen(runinfo_url)
    lines = r.read().split("\n")
    keys   = lines[0].split(",")
    values = lines[1].split(",")
    runinfo = dict(zip(keys, values))
    return runinfo

def ftp_download_single_run(run_accession):
    """ use ftp to download one sra file 
    one advantage of this is that it does not leave large file in $HOME/ncbi/public/sra/
    """
    sra_file_url = "ftp://ftp-trace.ncbi.nih.gov/sra/sra-instant/reads/ByRun/sra/%s/%s/%s/%s.sra"%(run_accession[:3], run_accession[:6], run_accession, run_accession)
    with open(run_accession+".sra", 'wb') as OUT:
        response = urllib2.urlopen(sra_file_url)
        shutil.copyfileobj(response, OUT)

def fastqDumpExistingSraFile(file_name, splitFiles = False):
    """ assumes fastq-dump is on path """
    command = ["fastq-dump"]
    if splitFiles:
        command.append("--split-files")
    command.append(file_name)
    subprocess.call(command, shell=False)

def get_run_ids(run_meta):
    run_ids = []
    for run in run_meta:
        run_ids.append(run['run_id'])
    return run_ids

def download_fastq_files(fasterq_dump_loc, output_dir, run_ids, gzip_output=True):

    # use the new fasterq-dump utility (faster, but doesn't have filtering option which results in bigger files)
    fasterq_dump_cmd_template = Template('$fasterq_dump_bin --outdir $out_dir --split-files -f $id')

    # for each run, download the fastq file
    for run_id in run_ids:
        fasterq_dump_cmd = fasterq_dump_cmd_template.substitute(fasterq_dump_bin=fasterq_dump_loc, id=run_id, out_dir=output_dir)

        # call fasterq-dump
        try:
            print 'executing \'' + fasterq_dump_cmd + '\''
            result = subprocess.check_output([fasterq_dump_cmd], shell=True)
        except subprocess.CalledProcessError as e:
            return_code = e.returncode

        # gzip the output; gzip will skip anything already zipped
        if gzip_output:
            gzip_cmd = 'gzip '+output_dir+'/*.fastq'
            subprocess.call(gzip_cmd, shell=True)

    return

def download_sra_data(fasterq_dump_loc, fastq_output_dir, accession_id, metaonly, compress_files, metadata_file):

    # ===== 1. Get the metadata for each run
    metadata = get_accession_metadata(accession_id)

    # ===== 2. Get the fastq files for each run
    if not metaonly:
        download_fastq_files(fasterq_dump_loc, fastq_output_dir, get_run_ids(metadata), gzip_output=compress_files)
        print 'Fastq Filenames:'
        print(glob.glob(fastq_output_dir+'/*.fastq*'))
        for run in metadata:
            run_id = run.get("run_id",None)
            files = glob.glob(os.path.join(fastq_output_dir,"*"+run_id+"*"))
            run['files']=[os.path.basename(f) for f in files]

    # ===== 3. Pack it into the output JSON
    print 'Metadata:'
    print json.dumps(metadata, indent=1)
    if metadata_file:
        fp = file(metadata_file, "w")
        json.dump(metadata, fp, indent=2)
        fp.close()


    # ===== 4. Add everything to the workspace (?)
