from flask import Flask
from flask import render_template, Markup, g, request, jsonify, redirect, Response, flash, url_for
import operator
import os
from collections import defaultdict
from managers import db_conn, study_manager, sample_manager, variant_manager, filter_manager, uniprot_manager
import annotation
from bson import json_util
from constants import VARIANT_EFFECTS, VARIANT_RANKS, VARIANT_SHORTNAMES
import numpy as np
import redis
from werkzeug import secure_filename


UPLOAD_FOLDER = '/Volumes/achiever_vol2/UPLOADS/'
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
    var_mgr = variant_manager(db="test",conn=g.conn)
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
def json_variants(return_query=False):
    """
    Parses set of query arguments and retrieves records
    from mongodb. Re-formats some data fields and jenkily adds
    some HTML formatting to some of them. Returns a json object
    which is passed to the javascript datatable on the view_variants
    page. Also creates an appropriate title for the view_variants page.

    This function:
        - Make basic determination if query is:
            + for a specific sample
            + for a specific gene
            + for a range of chromosome:start-stop
        - includes/excludes columns based on the `columns` parameter and
            parses this list to handle dot notation (annotations.EFF...)
        - Sets a maximum limit of returned rows
        - parses the include_filters and exclude_filters lists
        - sets up the mongodb groupby clause if this is requested
        - Lastly, iterates across the returned raw database records
            and reformats into a flat n x m table, adding HTML fields 
            for formatting etc.

    Todo: 
        - split apart into its own class/API
        - HTML formatting should not be added here... 
            (unless clearly asked for in the request)
        - Better handling of limits/skipby requests
        - Improve the custom columns parsing (unreadable code right now)
        - Integrate output options for CSV etc.

    """
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

    default_column_list = ["chrom","start","end","sample_name","id","ref","alt"]
    projection = {"sample_name": True, 
                  "id":True,
                  "ref": True,
                  "alt": True,
                  "chrom":True,
                  "start":True,
                  "filter": True,
                  "annotations.EFF":True}
    
    custom_column_list = []
    if is_arg("columns"):
        for c in request.args["columns"].rstrip(";").split(";"):
            c = c.split(".")
            if len(c) == 1:
                custom_column_list.append(c)
                projection[c[0]] = True
            elif (c[0] == "annotations") and (c[1] == "EFF"):
                custom_column_list.append(c)
            elif (c[0] == "annotations") and (c[1] == "dbNSFP"):
                custom_column_list.append(c)
                projection["annotations.dbNSFP." +c[2]] = True
            else:
                pass

    # FILTERS
    if ("exclude_filters" in request.args) and len(request.args["exclude_filters"]) > 0:
        query["filter"]["$nin"] = request.args["exclude_filters"].split(";")
    if ("include_filters" in request.args)  and len(request.args["include_filters"]) > 0:
        for f in request.args["include_filters"].strip(";").split(";"):
            filter_type, filter_id = f.split(":")
            filter_mgr = filter_manager(db="test",conn=g.conn)
            filter_obj = filter_mgr.get_filter(filter_id)[0]
            if filter_type == "set":
                query["filter"]["$in"].append(filter_id)
            elif "query_repr" in filter_obj:
                qr = filter_obj["query_repr"]
                for i in qr:
                    field = i["field"]
                    op = i["op"]
                    value = i["value"]
                    query[field][op] = value
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

        print query
        if len(query) == 0:
            #query = {"_id":{"$ne":""}}
            query = {}
            data = g.conn["test"].variants.find(spec=query,fields=projection).skip(0).limit(limit)
        else:
            data = g.conn["test"].variants.find(spec=query,fields=projection).skip(0).limit(limit).sort([("chrom", 1), ("start", 1)])

    out = {}
    out["aaData"] = []

    for row in data:
        if grouped:
            row["annotations"] = {"EFF":row["annotations"][0]}
            row["filter"] = row["filter"][0]
            row["sample_name"] = int(row["count"]) #", ".join(row["sample_name"])

        row_data = [row.get(c,'') for c in default_column_list]
        row_data.append("".join(["<div class='filter-tag %s'></div>" % f for f in row["filter"]]))
        highest_rank = 0
        effect_str = ""
        gene_str = ""
        
        for eff in row["annotations"].get("EFF",[]):
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
        
        if len(custom_column_list) > 0:
            for c in custom_column_list:
                if len(c) == 1:
                    row_data.append(row.get(c[0],''))
                else:
                    if c[1] == "EFF":
                        try:
                            val = row[c[0]][c[1]][0].get(c[2], '')
                            row_data.append(val)
                        except KeyError:
                            row_data.append('')
                    elif c[1] == "dbNSFP":
                        try:
                            val =row[c[0]][c[1]].get(c[2],'')
                            row_data.append(val)
                        except KeyError:
                            row_data.append('')

        out["aaData"].append(row_data)
    
    
    if return_query:
        return json_util.dumps(query)
    else:
        return jsonify(out)

@app.route('/_variants_query.json', methods=['GET'])
def variant_query_test():
    """
    This only returns the mongodb query that would be used
    to get a list of variants. Testing/debug only.
    """
    return json_variants(return_query=True)


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
