import argparse
import sys
import pprint
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../code/")
from managers import *
import pandas as pd
from cStringIO import StringIO
from bson.objectid import ObjectId
import datetime


formatters = {'AB': float,
              'AC': float,
              'AF': float,
              'AN': float,
              'Alignability': float,
              'BaseQRankSum': float,
              'DB': float,
              'DP': float,
              'Dels': float,
              'EFF': None,
              'HRun': float,
              'LowMQ': lambda x: [float(y) for y in x.split(",")],
              'MQ': float,
              'MQ0': float,
              'MQRankSum': float,
              'QD': float,
              'SB': float,
              'dbNSFP_1000Gp1_AC': float,
              'dbNSFP_1000Gp1_AFR_AC': float,
              'dbNSFP_1000Gp1_AMR_AC': float,
              'dbNSFP_1000Gp1_ASN_AC': float,
              'dbNSFP_1000Gp1_EUR_AC': float,
              'dbNSFP_29way_logOdds': float,
              'dbNSFP_29way_pi': lambda x: [float(y) for y in x.split(":")],
              'dbNSFP_Ancestral_allele': str,
              'dbNSFP_ESP6500_AA_AF': float,
              'dbNSFP_ESP6500_EA_AF': float,
              'dbNSFP_FATHMM_score': float,
              'dbNSFP_GERP++_NR': float,
              'dbNSFP_GERP++_RS': float,
              'dbNSFP_LRT_Omega': float,
              'dbNSFP_LRT_score': float,
              'dbNSFP_MutationAssessor_score': float,
              'dbNSFP_MutationTaster_score': float,
              'dbNSFP_Polyphen2_HDIV_score': lambda x: [float(y) for y in x.split(",")],
              'dbNSFP_Polyphen2_HVAR_score': lambda x: [float(y) for y in x.split(",")],
              'dbNSFP_SIFT_score': float,
              'dbNSFP_SLR_test_statistic': float,
              'dbNSFP_Uniprot_id': lambda x: x.split(","),
              'dbNSFP_Ensembl_transcriptid': lambda x: x.split(","),
              'dbNSFP_phyloP': float}

short_key_names = {'Alignability': 'ALI',
                   'BaseQRankSum': 'BQRS',
                   'MQRankSum': 'MQRS',
                   'dbNSFP_1000Gp1_AC': '1gALLac',
                   'dbNSFP_1000Gp1_AFR_AC': '1gAFRac',
                   'dbNSFP_1000Gp1_AMR_AC': '1gAMRac',
                   'dbNSFP_1000Gp1_ASN_AC': '1gASNac',
                   'dbNSFP_1000Gp1_EUR_AC': '1gEURac',
                   'dbNSFP_29way_logOdds': '29wayLO',
                   'dbNSFP_29way_pi': '29wayPi',
                   'dbNSFP_Ancestral_allele': 'AncAll',
                   'dbNSFP_ESP6500_AA_AF': 'ESPaa',
                   'dbNSFP_ESP6500_EA_AF': 'ESPea',
                   'dbNSFP_FATHMM_score': 'FATHMM',
                   'dbNSFP_GERP++_NR': 'GERPnr',
                   'dbNSFP_GERP++_RS': 'GERPrs',
                   'dbNSFP_LRT_Omega': 'LRTo',
                   'dbNSFP_LRT_score': 'LRTs',
                   'dbNSFP_MutationAssessor_score': 'MAs',
                   'dbNSFP_MutationTaster_score': 'MTs',
                   'dbNSFP_Polyphen2_HDIV_score': 'P2hdiv',
                   'dbNSFP_Polyphen2_HVAR_score': 'P2hvar',
                   'dbNSFP_SIFT_score': 'SIFT',
                   'dbNSFP_SLR_test_statistic': 'SLR',
                   'dbNSFP_Uniprot_id': 'UPid',
                   'dbNSFP_Ensembl_transcriptid': 'ETID',
                   'dbNSFP_phyloP': 'PyP'}

                    
def read_vcf(vcf_filename, columns=None):
    columns = None
    s = StringIO()
    vcf_header_lines = ""
    with open(vcf_filename) as f:
        for line in f:
            if line.startswith('#'):
                 if line.startswith('#CHROM'):
                       columns = line.lstrip("#").split()
                 vcf_header_lines += line
            else:
                s.write(line)
    s.seek(0)
    df = pd.read_csv(s, sep="\t",names=columns)
    return df, vcf_header_lines, columns

def parse_annotations(info_field):
    field_list = info_field.split(";")
    out = {}
    for field in field_list:
        try:
            key, value = field.split("=")
        except ValueError:
            key, value = field, True
        if key == "EFF":
            # this is the SNPEFF field, parse it appropriately
            #NON_SYNONYMOUS_CODING(MODERATE|MISSENSE|Gtt/Att|V5I|293|HNRNPCL1||CODING|NM_001013631.1|2|1),
            #MODERATE|MISSENSE|cGc/cCc|R1113P|1159|INPP5D||CODING|NM_005541.3|25|1|WARNING_TRANSCRIPT_INCOMPLETE
            EFF_LIST = []
            for effect in value.split(","):
                EFF = {}
                EFF["e"], t = effect.split("(",2)
                try:
                    # no optional warning field
                    _, EFF["f"], EFF["cc"], EFF["aa"], _, EFF["g"], _, _, EFF["tx"], EFF["r"], _ = t.split("|")
                except:
                    _, EFF["f"], EFF["cc"], EFF["aa"], _, EFF["g"], _, _, EFF["tx"], EFF["r"], _, EFF["err"] = t[:-1].split("|") #-1 removes trailing ")"
                # clear out any empty fields!
                EFF_LIST.append({k:v for k,v in EFF.iteritems() if v is not ''})
            out["EFF"] = EFF_LIST
        elif key[0:6] == "dbNSFP":
            # These are tne dbNSFP fields, process them appropriately!
            if "dbNSFP" not in out:
                out["dbNSFP"] = {}
            try:
                k = short_key_names.get(key,key)
                out["dbNSFP"][k] = formatters[key](value)
            except ValueError:
                print key, value
        else:
            k = short_key_names.get(key,key)
            try:
                out[k] = formatters[key](value)
            except KeyError:
                out[k] = value
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vcf", help="VCF file to import")
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument("--study_name", type=str, action="store", required=True)
    parser.add_argument("--study_desc", type=str, action="store", required=False, default="Study Description")
    parser.add_argument("--filter_name", type=str, action="store", required=True)
    parser.add_argument("--skip_samples", type=bool, action="store", required=False, default=False)

    args = parser.parse_args()
    print args
    args.vcf = os.path.realpath(args.vcf)
    # Read VCF file
    vcf_data, header_data, columns = read_vcf(args.vcf)
    
    sampleIDs = columns[10:]

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

    for sampleID in sampleIDs:
        try:
            sample_id = sample_mgr.get_sample(sampleID)["_id"]
        except TypeError:
            # sample doesnt exist yet, insert it!
            if args.dry:
                print "Add new sampleID to database: %s" % sampleID
            else:
                sample_mgr.insert_sample(sampleID, study_id, args.study_name)
                sample_id = sample_mgr.get_sample(sampleID)["_id"]
        finally:
            # insert the new meta data
            file_dict = {"filename": args.vcf,
                         "filetype": "vcf",
                         "metadata": {"vcf_header": header_data},
                         "filter_name": args.filter_name,
                         "date_imported": datetime.datetime.today()}
            if args.dry:
                print "Add new sample meta to database: %s" % sampleID
                print file_dict 
            else:
                sample_mgr.add_file_to_sample(sampleID, file_dict)

        for ix, row in vcf_data.iterrows():

            data = row[sampleID]
            dd = dict(zip(data.split(":"), row["FORMAT"]))
            if "FGT" in dd:
                if dd["FGT"] == "0/0":
                    continue
            elif "GT" in dd:
                if dd["FGT"] == "0/0":
                    continue

            if row["FILTER"] not in [".", "0", ""]:
                filters = [args.filter_name, row["FILTER"]]
            else:
                filters = [args.filter_name]

            if row["ID"] != ".":
                id_tag = row["ID"]
            else:
                id_tag = None

            annotations = parse_annotations(row["INFO"])

            if args.dry:
                print "\t".join(sampleID, str(row["CHROM"]), int(row["POS"]), id_tag, row["REF"], row["ALT"], row["QUAL"], filters)
                pprint.pprint(dd, width=160)
                pprint.pprint(annotations, width=160)
                print "--------------"
            else:
                var_mgr.insert_variant_from_vcf(sample_id=sample_id, 
                                            sample_name=sampleID, 
                                            chrom=str(row["CHROM"]),
                                            pos=int(row["POS"]), 
                                            id=id_tag,
                                            ref=row["REF"],
                                            alt=row["ALT"],
                                            qual=row["QUAL"],
                                            filters=filters,
                                            data=data,
                                             **annotations)
