
from string import Template
import subprocess
import csv

accession_id = 'SRP039561'

# ===== 1. Get the list of runs for an accession

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

# ===== 2. Get the metadata for each run

# format the run ids
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

# ===== 3. Get the fastq files for each run

fasterq_dump_bin = 'sra_toolkit/sratoolkit.2.9.1-1-mac64/bin/fasterq-dump'
fasterq_dump_cmd_template = Template(fasterq_dump_bin + ' --outdir tmp --split-files -f $id')

for run in metadata:
    fasterq_dump_cmd = fasterq_dump_cmd_template.substitute(id=run['Run'])

    # call fasterq-dump
    try:
        result = subprocess.check_output([fasterq_dump_cmd], shell=True)
    except subprocess.CalledProcessError as e:
        return_code = e.returncode

# 
