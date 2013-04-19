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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vcf", type=str, action="store", required=True)
    parser.add_argument("--study_name", type=str, action="store", required=True)
    parser.add_argument("--study_desc", type=str, action="store", required=False, default="Study Description")
    parser.add_argument("--filter_name", type=str, action="store", required=True)
    parser.add_argument("--sample_name", type=str, action="store", required=True)

    args = parser.parse_args()
    print args
    args.vcf = os.path.realpath(args.vcf)
    # Read VCF file
    vcf_data, header_data = read_vcf(args.vcf)

    # connect and set up all the mr. managers
    conn = db_conn().connect()
    var_mgr = variant_manager(db="test", conn=conn)
    sample_mgr = sample_manager(db="test", conn=conn)
    study_mgr = study_manager(db="test", conn=conn)
    
    try:
        study_id = study_mgr.get_study(args.study_name)["_id"]
    except TypeError:
        # study doesnt exist, create it
        study_mgr.insert_study(args.study_name, args.study_desc)
        study_id = study_mgr.get_study(args.study_name)["_id"]

    try:
        sample_id = sample_mgr.get_sample(args.sample_name)["_id"]
    except TypeError:
        # sample doesnt exist yet, insert it!
        print args.sample_name, study_id
        sample_mgr.insert_sample(args.sample_name, study_id)
        sample_id = sample_mgr.get_sample(args.sample_name)["_id"]
    finally:
        # insert the new meta data
        file_dict = {"filename": args.vcf,
                 "filetype": "vcf",
                 "metadata": {"vcf_header": header_data},
                 "filter_name": args.filter_name    ,
                 "date_imported": datetime.datetime.today()}
        sample_mgr.add_file_to_sample(args.sample_name, file_dict)



    for ix, row in vcf_data.iterrows():
        if row["FILTER"] != "0":
            filters = [args.filter_name, row["FILTER"]]
        else:
            filters = [args.filter_name]

        var_mgr.insert_variant_from_vcf(sample_id=sample_id, 
                                        sample_name=args.sample_name, 
                                        chrom=str(row["CHROM"]),
                                        pos=int(row["POS"]), 
                                        id=row["ID"],
                                        ref=row["REF"],
                                        alt=row["ALT"],
                                        qual=row["QUAL"],
                                        filters=filters,
                                        data=row["DATA"],
                                         **parse_info(row["INFO"]))
