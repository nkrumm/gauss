from flask import Flask
from flask import render_template, Markup, g
import operator
from managers import db_conn, study_manager, sample_manager, variant_manager

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
    return render_template("study_info.html", study_name=study_name, info=info)

@app.route('/samples')
def samples():
    mgr = sample_manager(db="test",conn=g.conn)
    rows = mgr.get_all_samples()
    return render_template("samples.html", sample_rows=rows, columns=["identifier", "attributes"])


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
@app.route('/samples/<sample_name>/variants')
def get_variants(gene=None, sample_name=None, chrom=None, start=None, end=None, variant_id=None):
    var_mgr = variant_manager(db="test",conn=g.conn)
    if variant_id is not None:
        data = var_mgr.get_variant(variant_id)
        #data["sample_name"] = "test"
        return render_template("variant_details.html", data=data)
    else:
        if sample_name is not None:
            sample_mgr = sample_manager(db="test", conn=g.conn)
            sample_id = sample_mgr.get_sample(sample_name)["_id"]
            data = var_mgr.documents.find({"sample_id":sample_id})
            title = "%s (All Variants)" % sample_name
        elif gene is not None:
            data = var_mgr.get_variants_by_gene(gene)
            title = "<em>%s</em> (All Variants)" % gene
        elif chrom is not None:
            chrom_int = int(chrom.lower().replace("chr",""))
            title="%s: %s - %s" % (chrom, start, end)
            data = var_mgr.get_variants_by_position(chrom_int, int(start), int(end))
        return render_template("view_variants.html", title=Markup(title), data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
