from flask import Flask
from flask import render_template, Markup, g, request, jsonify, redirect
import operator
import os
from collections import defaultdict
from managers import db_conn, study_manager, sample_manager, variant_manager, filter_manager
import annotation
from bson import json_util
from constants import VARIANT_EFFECTS, VARIANT_RANKS, VARIANT_SHORTNAMES
import numpy as np
from werkzeug import secure_filename

UPLOAD_FOLDER = '/Volumes/achiever_vol2/UPLOADS/'
ALLOWED_EXTENSIONS = set(['vcf','variant','txt','bed'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def before_request():
    g.conn = db_conn().connect()

@app.teardown_request
def teardown_request(exception):
    g.conn.close()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/studies')
def studies():
    study_mgr = study_manager(db="test",conn=g.conn)
    study_rows = study_mgr.get_all_studies()
    return render_template("studies.html", study_rows=study_rows, columns=["study_name","study_description", "date_added"])

@app.route('/studies/<study_name>/')
def study_info(study_name):
    study_mgr = study_manager(db="test",conn=g.conn)
    info = study_mgr.get_study(study_name)
    return render_template("study_info.html", study_name=study_name, data=info)

@app.route('/samples')
def samples():
    mgr = sample_manager(db="test",conn=g.conn)
    rows = mgr.get_all_samples()
    return render_template("samples.html", sample_rows=rows, columns=["sample_id","study_name", "attributes"])


@app.route('/samples/<sample_id>')
def samples_info(sample_id):
    mgr = sample_manager(db="test",conn=g.conn)
    var_mgr = variant_manager(db="test",conn=g.conn)
    data = mgr.get_sample(sample_id = sample_id)
    effect_summary = var_mgr.get_sample_variant_summary(data["_id"])
    for row in effect_summary:
        eff_code = row["_id"]
        eff_type = VARIANT_EFFECTS[eff_code]
        eff_rank = VARIANT_RANKS[eff_type]
        row["effect_str"] = Markup("<span class='label impact-tag %s'>%s</span>" % (eff_type, VARIANT_SHORTNAMES[eff_code]))
        row["effect_rank"] = eff_rank
    print map(operator.itemgetter("effect_rank"), effect_summary)
    rank_sort = np.argsort(map(operator.itemgetter("effect_rank"), effect_summary))
    data["variant_summary"] = [effect_summary[i] for i in rank_sort[::-1]]
    return render_template("sample_info.html", sample_id=sample_id, info=data)

@app.route('/variants/')
def variants():
    var_mgr = variant_manager(db="test",conn=g.conn)
    stats = var_mgr.get_db_stats()
    return render_template("variants.html", stats=stats)

@app.route('/genotypes/id:<genotype_id>')
def genotype_details(genotype_id):
    var_mgr = variant_manager(db="test",conn=g.conn)
    data = var_mgr.get_variant(genotype_id)
    for ix, row in enumerate(data["annotations"]["EFF"]):
        data["annotations"]["EFF"][ix]["effect_code"] = VARIANT_EFFECTS[row["e"]]
    return render_template("genotype_details.html", data=data)

@app.route('/variants/id:<chrom>:<start>')
@app.route('/variants/id:<chrom>:<start>-<end>')
def variant_details(chrom, start, end=None):
    var_mgr = variant_manager(db="test",conn=g.conn)

    if end is None:
        genotype_data = var_mgr.get_variants_by_position(chrom, start)
    else:
        genotype_data = var_mgr.get_variants_by_position(chrom, start, end)
    
    
    variant_data = var_mgr.get_variant(genotype_data[0]["_id"])
    for ix, row in enumerate(variant_data["annotations"]["EFF"]):
        variant_data["annotations"]["EFF"][ix]["effect_code"] = VARIANT_EFFECTS[row["e"]]
    return render_template("variant_details.html", variant_data=variant_data, genotype_data=genotype_data)

@app.route('/all_variants/')    
@app.route('/variants/<gene>')
@app.route('/variants/<chrom>:<start>-<end>')
@app.route('/samples/<sample_id>/variants')
def get_variants(gene=None, sample_id=None, chrom=None, start=None, end=None):
    var_mgr = variant_manager(db="test",conn=g.conn)
    if sample_id is not None:
        title = "%s" % sample_id
        query_string = "sample_id=%s" % sample_id

    elif gene is not None:
        title = "<em>%s</em>" % gene
        query_string = "gene=%s" % gene

    elif chrom is not None:
        chrom_int = int(chrom.lower().replace("chr",""))
        title="%s: %s - %s" % (chrom, start, end)
        query_string = "chrom=%s&start=%s&end=%s" % (chrom, start, end)
    else:
        title = 'All variants'
        query_string = ""

    filter_mgr = filter_manager(db="test",conn=g.conn)
    filters = filter_mgr.get_all_filters()
    return render_template("view_variants.html", title=Markup(title), query_string=Markup(query_string), filters=filters)

def is_arg(argname):
    return (argname in request.args) and (len(request.args[argname]) > 0)

@app.route('/_variants.json', methods=['GET'])
def json_variants(return_query=False):
    query = defaultdict(lambda: defaultdict(list))

    var_mgr = variant_manager(db="test",conn=g.conn)
    # INITIAL DATA
    if is_arg("sample_id"):
        sample_mgr = sample_manager(db="test", conn=g.conn)
        sample_id = sample_mgr.get_sample(request.args["sample_id"])["_id"]
        query["sample_id"] = sample_id
        title = "%s (All Variants)" % request.args["sample_id"]

    if is_arg("gene"):
        query["annotations.EFF.g"] = request.args["gene"]
        title = "<em>%s</em> (All Variants)" % request.args["gene"]

    if is_arg("chrom") and is_arg("start") and is_arg("end"):
        chrom = request.args["chrom"].lower().replace("chr","")
        #chrom = request.args["chrom"]
        start = int(request.args["start"])
        end = int(request.args["end"])
        query["chrom"] = chrom
        query["start"] = {'$gte': start, '$lte': end}
        title="%s: %d - %d" % (chrom, start, end)

    if is_arg("limit"):
        limit = int(request.args["limit"])
    else:
        limit = 1000

    # FILTERS
    if ("exclude_filters" in request.args) and len(request.args["exclude_filters"]) > 0:
        query["filter"]["$nin"] = request.args["exclude_filters"].split(";")
    if ("include_filters" in request.args)  and len(request.args["include_filters"]) > 0:
        for f in request.args["include_filters"].strip(";").split(";"):
            filter_type, filter_id = f.split(":")
            if filter_type == "set":
                query["filter"]["$in"].append(filter_id)
            elif filter_type == "attr":
                if filter_id == "truncating":
                    query["annotations.EFF.e"]["$in"]=["FRAME_SHIFT", "STOP_GAINED"]
                elif filter_id == "autosomal":
                    query["chrom"]["$nin"]=["X","Y"]
                elif filter_id == "sex_chrs":
                    query["chrom"]["$in"]=["X","Y"]
                elif filter_id == "dbSNP":
                    query["id"] = None
                elif filter_id == "genic":
                    if not is_arg("gene"):  # only do this if not already a gene query
                        query["annotations.EFF.g"]["$ne"]=None
                elif filter_id == "exonic":
                    if not is_arg("gene"):  # only do this if not already a gene query
                        query["annotations.EFF.g"]["$ne"]=None
                    query["annotations.EFF.e"]["$nin"] = ["INTRON","UTR-5","UTR-3","INTRAGENIC","UTR_3_PRIME","UTR_5_PRIME"]
                elif filter_id == "GATK_filter":
                    query["filter"]["$nin"].append(filter_id)


    projection = {"sample_name": True, 
                      "id":True,
                      "ref": True,
                      "alt": True,
                      "chrom":True,
                      "start":True,
                      "filter": True,
                      "annotations.EFF":True}
    if is_arg("group") and (request.args["group"] == "variant"):
        grouped = True
        data = var_mgr.documents.aggregate([{"$match": query},
                                      
                                      {"$group": {"_id":{"chrom":"$chrom",
                                                      "start":"$start",
                                                      "end":"$end",
                                                      "id":"$id",
                                                      "ref":"$ref",
                                                      "alt":"$alt",
                                                      },
                                               "count": { "$sum": 1},
                                               "annotations_list": {"$addToSet":"$annotations.EFF"},
                                               "sample_name_list": {"$addToSet":"$sample_name"},
                                               "filter":  {"$addToSet":"$filter"},
                                               }},
                                      {"$project":{
                                            "_id": {"$add": [0]}, # this is a stupid hack to put a literal/static field in
                                            "chrom": "$_id.chrom",
                                            "start": "$_id.start",
                                            "end": "$_id.end",
                                            "ref": "$_id.ref",
                                            "alt": "$_id.alt",
                                            "id": "$_id.id",
                                            "count": "$count",
                                            "annotations": "$annotations_list",
                                            "sample_name":"$sample_name_list",
                                            "filter": "$filter"

                                      }},
                                      {"$sort": {"chrom": 1, "start": 1}}

                                      ])
        #return jsonify(data)
        data = data["result"]


    else:
        grouped = False
        if len(query) == 0:
            #query = {"_id":{"$ne":""}}
            query = {}
            data = g.conn["test"].variants.find(spec=query,fields=projection).skip(0).limit(limit)
        else:
            data = g.conn["test"].variants.find(spec=query,fields=projection).skip(0).limit(limit).sort([("chrom", 1), ("start", 1)])
    
        
    out = {}
    out["aaData"] = []
    column_list = ["chrom","start","end","sample_name","id","ref","alt"]
    for row in data:
        if grouped:
            row["annotations"] = {"EFF":row["annotations"][0]}
            row["filter"] = row["filter"][0]
            row["sample_name"] = int(row["count"]) #", ".join(row["sample_name"])

        row_data = [row.get(c,'') for c in column_list]
        row_data.append("".join(["<div class='filter-tag %s'></div>" % f for f in row["filter"]]))
        highest_rank = 0
        effect_str = ""
        gene_str = ""
        
        for eff in row["annotations"]["EFF"]:
            eff_code = eff.get("e", None)
            eff_type = VARIANT_EFFECTS[eff_code]
            eff_rank = VARIANT_RANKS[eff_type]
            if eff_rank > highest_rank:
                eff_gene = eff.get("g", None)
                if (eff_type in ["high", "moderate", "low"]) and (eff_gene is not None):
                    gene_str = eff_gene
                    effect_str = "<span class='label impact-tag %s'>%s</span>" % (eff_type, VARIANT_SHORTNAMES[eff_code])
        
        row_data.append(gene_str)
        if grouped:
            if row["end"] is not None:
                pos_str = '%s:%d-%d' % (row["chrom"], row["start"], row["end"])
            else:
                pos_str = '%s:%d' % (row["chrom"], row["start"])
            row_data.append("<a href='/variants/id:%s'>%s</a>" % (pos_str, effect_str))
            row_data.append("<a href='/variants/id:%s'>id</a>" % (pos_str))
        else:
            row_data.append("<a href='/genotypes/id:%s'>%s</a>" % (row["_id"], effect_str))
            row_data.append("<a href='/genotypes/id:%s'>id</a>" % row["_id"])
        out["aaData"].append(row_data)
    
    
    if return_query:
        return json_util.dumps(query)
    else:
        return jsonify(out)

@app.route('/_variants_query.json', methods=['GET'])
def variant_query_test():
    return json_variants(return_query=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS



@app.route('/filters', methods=['GET', 'POST'])
def filters():
    filter_mgr = filter_manager(db="test",conn=g.conn)

    if request.method == 'POST':
        file_obj = request.files['file']
        filetype = request.form["filetype"]
        filter_name = request.form["filter_name"]
        filter_desc = request.form["filter_desc"]
        if file_obj and allowed_file(file_obj.filename):
            filename = secure_filename(file_obj.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_obj.save(save_path)
            
            filter_mgr.create_filter(filter_name, filter_desc)
            if filetype=='gene':
                worker = annotation.GeneAnnotationWorker(save_path, "test", g.conn)
                worker.start(filter_name)

        redirect('/filters')

    rows = filter_mgr.get_all_filters()
    return render_template("filters.html", rows=rows, columns=["filter_name","description", "type", "date_added","color"])

@app.route('/filters.json')
def jsonfilters():
    filter_mgr = filter_manager(db="test",conn=g.conn)
    rows = filter_mgr.get_all_filters()
    return jsonify(result=[i for i in rows])



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
