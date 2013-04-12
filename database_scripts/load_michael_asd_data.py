import argparse
import sys
sys.path.append("/net/eichler/vol8/home/nkrumm/cuttlefish/code/")
from managers import *
import pandas
from bson.objectid import ObjectId


parser = argparse.ArgumentParser()
parser.add_argument("--infile", type=str, action="store", required=True)
parser.add_argument("--study_name", type=str, action="store", required=True)

args = parser.parse_args()
print args

conn = db_conn().connect()

header = ["Type", "Gene", "chrom", "start", "end", "Ref", "Alt", "GenotypeInfo_mother", "GenotypeInfo_father", "GenotypeInfo_proband", "Inheritance", "Family", "ID", "DOB", "Sex", "Ethnicity", "ADOS_CSS", "SRS_parent_t_score", "vineland_ii_composite_standard_score", "full_scale_iq", "verbal_iq", "nonverbal_iq", "livebirth", "birth_order", "family_structure", "height", "weight", "head_circumference", "bmi", "srs_parent_communication", "srs_parent_cognition", "srs_parent_motivation", "srs_parent_awareness", "srs_parent_mannerisms", "Mother_DOB", "mother_srs_adult_total", "mother_height", "mother_weight", "mother_head_circumference", "mother_bmi", "mother_ethnicity", "Father_DOB", "father_srs_adult_total", "father_height", "father_weight", "father_head_circumference", "father_bmi", "father_ethnicity", "Private", "Original_Set", "VariantType", "phyloPS_Score", "PolyPhen2Score", "esp6500_all_frequency", "dbSNP132", "mother_AB", "father_AB", "proband_AB", "Exonic Type", "Transcripts"]
df = pandas.read_csv(args.infile, names=header, sep="\t")

db = "test"
collection = "variants.%s" % args.study_name



var_mgr = variant_manager(db="test", conn=conn)
sample_mgr = sample_manager(db="test", conn=conn)
study_mgr = study_manager(db="test", conn=conn)

study_id = study_mgr.get_study(args.study_name)["_id"]

for sample_name in set(df["ID"]):
    df_sample = df[df.ID == sample_name]
    try:
        sample_id = sample_mgr.get_sample(sample_name)["_id"]
    except TypeError:
        # sample doesnt exist yet, insert it!
        print sample_name, study_id
        sample_mgr.insert_sample(sample_name, study_id)
        sample_id = sample_mgr.get_sample(sample_name)["_id"]

    for ix, row in df_sample.iterrows():

        annotations = {}
        annotations["gene"] = row["Gene"]
        annotations["type"] = row["Type"]
        var_mgr.insert_variant(sample_id,
                               int(row["chrom"]), int(row["start"]),
                               int(row["end"]), row["Ref"],
                               row["Alt"], **annotations)

