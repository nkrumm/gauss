from flask import Flask
from flask import render_template, Markup, g, request, jsonify, redirect, Response, flash, url_for
import operator
import os
from collections import defaultdict
from managers import db_conn, study_manager, sample_manager, variant_manager, filter_manager, uniprot_manager
import annotation
from query import GaussQuery
from bson import json_util
from constants import VARIANT_EFFECTS, VARIANT_RANKS, VARIANT_SHORTNAMES
import numpy as np
import redis
from werkzeug import secure_filename

import settings

UPLOAD_FOLDER = settings.UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['vcf', 'variant', 'txt', 'bed'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'some_secret'

def event_stream(pubsub):
    """
    Unfinished WebSockets streaming functions
    """
    # TODO: handle client disconnection.
    for message in pubsub.listen():
        yield 'data: %s\n\n' % message['data']

@app.route('/stream')
def stream():
    """
    Flask endpoint to receive streaming events via websockets
    Not fully implemented.
    """
    return Response(event_stream(g.pubsub),
                    mimetype="text/event-stream")

@app.before_request
def before_request():
    """
    Open database connections to Mongo and Redis (for python rq)
    `g` is the flask global variable
    """
    g.red = redis.StrictRedis()
    g.pubsub = g.red.pubsub()
    g.pubsub.subscribe('chat')
    g.conn = db_conn().connect()

@app.teardown_request
def teardown_request(exception):
    """
    Close db connection after each flask request
    Note that db connection pooling is used, so these actually 
    do stay open for some time.
    """
    g.conn.close()

@app.route('/')
def home():
    """
    Home Page
    """
    return render_template("index.html")

@app.route('/studies')
def studies():
    """
    Flask function to list of all available studies
    """
    study_mgr = study_manager(db="test",conn=g.conn)
    study_rows = study_mgr.get_all_studies()
    return render_template("studies.html", study_rows=study_rows, columns=["study_name","study_description", "date_added"])

@app.route('/studies/<study_name>/')
def study_info(study_name):
    """
    Flask function to show details of a particular study. 
    Nothing useful currently implemented here.
    """
    study_mgr = study_manager(db="test",conn=g.conn)
    info = study_mgr.get_study(study_name)
    return render_template("study_info.html", study_name=study_name, data=info)

@app.route('/samples')
def samples():
    """
    Flask function to show list of all samples in the database.
    """
    mgr = sample_manager(db="test",conn=g.conn)
    rows = mgr.get_all_samples()
    return render_template("samples.html", sample_rows=rows, columns=["sample_id","study_name", "files","attributes"])


@app.route('/samples/<sample_id>')
def samples_info(sample_id):
    """
    Flask function to return sample info page. Returns a summary of 
    the number of variants in this sample, as well as the files attached
    to this sample and metadata.
    """
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
    rank_sort = np.argsort(map(operator.itemgetter("effect_rank"), effect_summary))
    data["variant_summary"] = [effect_summary[i] for i in rank_sort[::-1]]
    return render_template("sample_info.html", sample_id=sample_id, info=data)

@app.route('/variants/')
def variants():
    """
    Flask function for variants home page. Various stats on the
    database are returned, not much else. A search box is provided
    as well.
    """
    var_mgr = variant_manager(db="test",conn=g.conn)
    stats = var_mgr.get_db_stats()
    return render_template("variants.html", stats=stats)

@app.route('/genotypes/id:<genotype_id>')
def genotype_details(genotype_id):
    """
    Flask function to return genotype info, dashboard, etc.
    """
    var_mgr = variant_manager(db="test",conn=g.conn)
    data = var_mgr.get_variant(genotype_id)
    if "EFF" in data["annotations"]:
        for ix, row in enumerate(data["annotations"]["EFF"]):
            data["annotations"]["EFF"][ix]["effect_code"] = VARIANT_EFFECTS[row["e"]]
    data["dashboard"] = {}
    data["dashboard"]["gatk"] = []
    data["dashboard"]["gatk"].append({"title": "QUAL", "score": data["qual"]})
    #data["dashboard"]["gatk"].append({"title": "DATA", "score": data["data"]})
    data["dashboard"]["gatk"].append({"title": "FILTER", "score": "GATK_filter" in data["filter"]})
    for name, value in data["annotations"].items():
        if name in ["MQ", "DP", "AB"]:
            data["dashboard"]["gatk"].append({"title": name, "score": value})

    if "dbNSFP" in data["annotations"]:
        data["dashboard"]["scores"] = []
        for score_name, score_value in data["annotations"]["dbNSFP"].items():
            print score_name, score_value
            data["dashboard"]["scores"].append({"title":score_name, "score": score_value})

        data["dashboard"]["freq"] = [{"title": "ESP", 
                                      "freqs": [{"pop":"AA", "freq": round(data["annotations"]["dbNSFP"].get("ESPaa", 0),3)},
                                                {"pop":"EA", "freq": round(data["annotations"]["dbNSFP"].get("ESPea", 0),3)}]},
                                     {"title": "1KG", "overallfreq": data["annotations"]["dbNSFP"].get("1gALLac", 0),
                                      "freqs": [{"pop":"AFR", "freq": data["annotations"]["dbNSFP"].get("1gAFRac",0)},
                                                {"pop":"EUR", "freq": data["annotations"]["dbNSFP"].get("1gEURac",0)},
                                                {"pop":"ASN", "freq": data["annotations"]["dbNSFP"].get("1gASNac",0)},
                                                {"pop":"AMR", "freq": data["annotations"]["dbNSFP"].get("1gAMRac",0)}]}]

    return render_template("genotype_details.html", data=data)

@app.route('/variants/id:<chrom>:<start>')
@app.route('/variants/id:<chrom>:<start>-<end>')
def variant_details(chrom, start, end=None):
    """
    Flask function to render the variant-level (not genotype) details
    Currently returns list of samples with this genotype.
    """
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
    """
    Flask function for variants endpoint. Sets up basic query string
    which is passed in to the javascript datatables AJAX call.
    """
    isoform = None
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
    return render_template("view_variants.html", title=Markup(title), query_string=Markup(query_string), filters=filters, isoform=isoform)

def is_arg(argname):
    """
    Helper function that returns true if argname is in list of GET/POST
    arguments passed to function by flask. Performs check to ensure
    that arguments were passed as well
    """
    return (argname in request.args) and (len(request.args[argname]) > 0)


@app.route('/_variants.json', methods=['GET'])
def _variants():
    query = GaussQuery(db="test", conn=g.conn)

    if is_arg("sample_id"):
        sample_mgr = sample_manager(db="test", conn=g.conn)
        sample_id = sample_mgr.get_sample(request.args["sample_id"])["_id"]
        query.add("sample_id", sample_id)

    if is_arg("gene"):
        query.add("annotations.EFF.g", request.args["gene"])

    if is_arg("isoform"):
        query.add("annotations.EFF.tx", request.args["isoform"])

    if is_arg("chrom") and is_arg("start") and is_arg("end"):
        chrom = request.args["chrom"].lower().replace("chr", "")
        start = int(request.args["start"])
        end = int(request.args["end"])
        query.add("chrom", chrom)
        query.add("start", {'$gte': start, '$lte': end})

    if is_arg("limit"):
        query.set_limit(request.args["limit"])

    if is_arg("skip"):
        query.set_skip(request.args["skip"])

    if is_arg("columns"):
        for c in request.args["columns"].rstrip(";").split(";"):
            query.add_column(c)

    if is_arg("exclude_filters"):
        for f in request.args["exclude_filters"].split(";"):
            query.add_exclude_filter(f)

    if is_arg("include_filters"):
        for f in request.args["include_filters"].strip(";").split(";"):
            query.add_include_filter(f)

    if is_arg("group"):
        query.set_grouping(request.args["group"])

    query.execute()

    return query.get_results(format="datatables")


def allowed_file(filename):
    """
    Used in uploading files for custom gene/variant sets.
    Tests if file extension is part of global ALLOWED_EXTENSIONS.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/annotation/dotest')
@app.route('/annotation/dotest/<n>')
def do_test_annotation(n=10):
    """
    Test function to see if Gauss Workers can do background
    work via python RQ
    """
    manager = annotation.GaussWorkerManager(db="test",conn=g.conn)
    worker = annotation.TestWorker()
    #manager.register_worker(worker)
    manager.start_worker(worker, args=[int(n)])
    flash("Ran a total of %d tests" % n, "success")
    return redirect(url_for("filters"))

@app.route('/annotation/doGeneAnnotationWorker',methods=['GET', 'POST'])
def do_GeneAnnotationWorker():
    """
    This function starts the GeneAnnotationWorker/Manager combo
    in order to add annotations for a set of upload genes in the POST
    variable
    """
    if request.method == 'POST':
        file_obj = request.files['file']
        filetype = request.form["filetype"]
        filter_name = request.form["filter_name"]
        filter_desc = request.form["filter_desc"]
        if file_obj and allowed_file(file_obj.filename):
            filename = secure_filename(file_obj.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_obj.save(save_path)
            if filetype=='type_gene':
                filter_mgr = filter_manager(db="test",conn=g.conn)
                filter_mgr.create_filter(filter_name, filter_desc)
                manager = annotation.GaussWorkerManager(db="test",conn=g.conn)
                worker = annotation.GeneAnnotationWorker2("mygeneworker")
                #manager.register_worker(worker)
                manager.start_worker(worker, args=(filter_name,save_path))
                flash("Job successfully queued", "success")
                return redirect(url_for("filters"))
    
    flash("Error in queueing job!", "error")
    return redirect("/filters")        


@app.route('/filters')
def filters():
    """
    Show a list of current filters and user-defined/uploaded
    sets.
    """
    filter_mgr = filter_manager(db="test",conn=g.conn)
    rows = filter_mgr.get_all_filters()
    return render_template("filters.html", rows=rows, columns=["filter_name","description", "type", "date_added","color"])

@app.route('/filters/delete/<name>')
def delete_filter(name):
    """
    Delete a user-defined set. It is not possible to delete filters
    defined by GAUSS
    """
    filter_mgr = filter_manager(db="test",conn=g.conn)
    filter_mgr.delete_filter(name)
    # manager = annotation.GaussWorkerManager(db="test",conn=g.conn)
    # worker = annotation.GeneAnnotationWorker2("mygeneworker")
    # manager.register_worker(worker)
    # manager.start_worker(worker, args=[filter_name]))
    flash("Filter successfully deleted","success")
    return redirect(url_for("filters"))

@app.route('/filters.json')
def jsonfilters():
    """
    Returns jsonified list of filters for use in AJAX calls
    and in modals that display current filters, etc
    """
    filter_mgr = filter_manager(db="test",conn=g.conn)
    rows = filter_mgr.get_all_filters()
    return jsonify(result=[i for i in rows])

@app.route('/jobs')
def jobs():
    """
    Shows currently queued, running, completed and failed
    GaussWorker jobs
    """
    job_mgr = annotation.GaussWorkerManager(db="test",conn=g.conn)
    rows = {}
    rows["queued"] = job_mgr.get_jobs(status="queued")
    rows["running"] = job_mgr.get_jobs(status="running")
    rows["completed"] = job_mgr.get_jobs(status="completed", limit=10)
    rows["failed"] =  job_mgr.get_jobs(status="failed", limit=10)
    return render_template("jobs.html", rows=rows, columns=["job_name","status", "type", "date_registered"])


@app.route('/uniprot/<refseq_accession>.json')
def uniprot_record(refseq_accession):
    """
    Returns jsonified record from the uniprot database.
    Used in geneplot drawing for domains, etc.
    """
    mgr = uniprot_manager(db="uniprot", conn=g.conn)
    data = mgr.get_uniprot_record_by_refseq_id(refseq_accession)
    print data[0]
    return jsonify(result=[i for i in data])

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    #http_server = WSGIServer(('', 5000), app)
    #http_server.serve_forever()
