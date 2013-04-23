from flask import Flask
from flask import render_template, Markup, g, request, jsonify
import operator
from collections import defaultdict
from managers import db_conn, study_manager, sample_manager, variant_manager, filter_manager
from bson import json_util
from constants import VARIANT_EFFECTS, VARIANT_RANKS, VARIANT_SHORTNAMES

app = Flask(__name__)

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
    data["variants"] = var_mgr.get_sample_variant_summary(data["_id"])

    return render_template("sample_info.html", sample_id=sample_id, info=data)

@app.route('/variants/')
def variants():
    return render_template("variants.html")

def variant_details():
    var_mgr = variant_manager(db="test",conn=g.conn)
    data = var_mgr.get_variant(variant_id)
    return render_template("variant_details.html", data=data)


@app.route('/variants/<gene>')
@app.route('/variants/<chrom>:<start>-<end>')
@app.route('/variants/id:<variant_id>')
@app.route('/samples/<sample_id>/variants')
def get_variants(gene=None, sample_id=None, chrom=None, start=None, end=None, variant_id=None):
    var_mgr = variant_manager(db="test",conn=g.conn)
    if variant_id is not None:
        data = var_mgr.get_variant(variant_id)
        for ix, row in enumerate(data["annotations"]["EFF"]):
            data["annotations"]["EFF"][ix]["effect_code"] = VARIANT_EFFECTS[row["e"]]
        return render_template("variant_details.html", data=data)
    else:
        if sample_id is not None:
            title = "%s (All Variants)" % sample_id
            query_string = "sample_id=%s" % sample_id

        elif gene is not None:
            title = "<em>%s</em> (All Variants)" % gene
            query_string = "gene=%s" % gene

        elif chrom is not None:
            chrom_int = int(chrom.lower().replace("chr",""))
            title="%s: %s - %s" % (chrom, start, end)
            query_string = "chrom=%s&start=%s&end=%s" % (chrom, start, end)

        return render_template("view_variants.html", title=Markup(title), query_string=Markup(query_string))

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

    # FILTERS
    if ("exclude_filters" in request.args) and len(request.args["exclude_filters"]) > 0:
        query["filter"]["$nin"] = request.args["exclude_filters"].split(";")
    if ("include_filters" in request.args)  and len(request.args["include_filters"]) > 0:
        query["filter"]["$in"] = request.args["include_filters"].split(";")

    projection = {"sample_name": True, 
                      "id":True,
                      "ref": True,
                      "alt": True,
                      "chrom":True,
                      "start":True,
                      "filter": True,
                      "annotations.EFF":True}

    data = var_mgr.documents.find(query,projection).sort([("chrom", 1), ("start", 1)])[0:1000]
    out = {}
    out["aaData"] = []
    column_list = ["chrom","start","end","sample_name","id","ref","alt"]
    for row in data:
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
        row_data.append("<a href='/variants/id:%s'>%s</a>" % (row["_id"], effect_str)) 
        row_data.append("<a href='/variants/id:%s'>id</a>" % row["_id"])
        out["aaData"].append(row_data)
    
    
    if return_query:
        return json_util.dumps(query)
    else:
        return jsonify(out)

@app.route('/_variants_query.json', methods=['GET'])
def variant_query_test():
    return json_variants(return_query=True)

@app.route('/filters')
def filters():
    filter_mgr = filter_manager(db="test",conn=g.conn)
    rows = filter_mgr.get_all_filters()
    return render_template("filters.html", rows=rows, columns=["filter_name","description", "type", "date_added","color"])

@app.route('/filters.json')
def jsonfilters():
    filter_mgr = filter_manager(db="test",conn=g.conn)
    rows = filter_mgr.get_all_filters()
    return jsonify(result=[i for i in rows])

@app.route('/testpage')
def test():
    return render_template("test.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
