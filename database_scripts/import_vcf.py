import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../code/")
from managers import *
import pandas
from cStringIO import StringIO
from bson.objectid import ObjectId
import datetime

def read_vcf(vcf_filename):
    s = StringIO()
    vcf_header_lines = ""
    with open(vcf_filename) as f:
        for line in f:
            if line.startswith('#'):
                vcf_header_lines += line
            else:
                s.write(line)
    s.seek(0)
    df = pandas.read_csv(s, sep="\t",names=["CHROM","POS","ID","REF","ALT","QUAL","FILTER","INFO","FORMAT","DATA"])
    return df, vcf_header_lines

def parse_info(info_field):
  return {x.split("=")[0]:x.split("=")[1] for x in info_field.split(";")}  

parser = argparse.ArgumentParser()
parser.add_argument("--vcf", type=str, action="store", required=True)
parser.add_argument("--study_name", type=str, action="store", required=True)
parser.add_argument("--sample_name", type=str, action="store", required=True)

args = parser.parse_args()
print args

# Read VCF file

vcf_data, header_data = read_vcf(args.vcf)

conn = db_conn().connect()
db = "test"
collection = "variants.%s" % args.study_name

var_mgr = variant_manager(db="test", conn=conn)
sample_mgr = sample_manager(db="test", conn=conn)
study_mgr = study_manager(db="test", conn=conn)

try:
    study_id = study_mgr.get_study(args.study_name)["_id"]
except TypeError:
    # study doesnt exist, create it
    study_mgr.insert_study(args.study_name, "Test Study")
    study_id = study_mgr.get_study(args.study_name)["_id"]

try:
    sample_id = sample_mgr.get_sample(args.sample_name)["_id"]
except TypeError:
    # sample doesnt exist yet, insert it!
    print args.sample_name, study_id
    file_metadata = {"filename": args.vcf,
                     "filetype": "vcf",
                     "metadata": {"vcf_header": header_data},
                     "date_imported": datetime.datetime.today()}

    sample_mgr.insert_sample(args.sample_name, study_id, file_metadata = file_metadata)
    sample_id = sample_mgr.get_sample(args.sample_name)["_id"]


for ix, row in vcf_data.iterrows():
    var_mgr.insert_variant_from_vcf(sample_id, 
                           args.sample_name, 
                           str(row["CHROM"]),
                           int(row["POS"]), 
                           row["ID"],
                           row["REF"],
                           row["ALT"],
                           row["QUAL"],
                           row["FILTER"],
                           row["DATA"],
                            **parse_info(row["INFO"]))
