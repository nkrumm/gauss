from bson import json_util
from flask import g, jsonify
from collections import defaultdict
from managers import db_conn, variant_manager, filter_manager
from constants import VARIANT_EFFECTS, VARIANT_RANKS, VARIANT_SHORTNAMES


class QueryException(Exception):
    pass


class GaussQuery(object):
    """docstring for GaussQuery"""
    def __init__(self, db, conn):
        super(GaussQuery, self).__init__()
        self.db = db
        self.conn = conn

        self.var_mgr = variant_manager(db=self.db, conn=self.conn)
        self.filter_mgr = filter_manager(db=self.db, conn=self.conn)

        self.column_list = ["chrom", "start", "end", "sample_name", "id", "ref", "alt"]
        self.custom_column_list = []
        self.projection = {k: True for k in self.column_list}
        #del self.projection["end"]  # may not be necessary
        self.projection["filter"] = True  # can add to column_list?
        self.projection["annotations.EFF"] = True  # can add to column list?
        self.grouped = False
        self.skip = 0
        self.limit = 1000
        self.query = defaultdict(lambda: defaultdict(list))

    def add(self, key, value):
        self.query[key] = value

    def set_limit(self, limit):
        self.limit = int(limit)

    def set_skip(self, skip):
        self.skip = int(skip)

    def add_column(self, column_name):
        c = column_name.split(".")
        if len(c) == 1:
            self.projection[column_name] = True
        elif c[1] != "EFF":  # EFF is ALREADY added to projection, do not want to double add
            self.projection[column_name] = True
        self.custom_column_list.append(c)

    def add_exclude_filter(self, filter_name):
        self.query["filter"]["$nin"].append(filter_name)

    def add_include_filter(self, filter_name):
        filter_type, filter_id = filter_name.split(":")
        filter_obj = self.filter_mgr.get_filter(filter_id)[0]
        if filter_type == "set":
            if "op" in filter_obj:
                self.query["filter"][filter_obj["op"]].append(filter_id)
            else:  # default to include filter
                self.query["filter"]["$in"].append(filter_id)
        elif "query_repr" in filter_obj:
            qr = filter_obj["query_repr"]
            for i in qr:
                field = i["field"]
                value = i["value"]
                if "op" in i:
                    op = i["op"]
                    self.query[field][op] = value
                else:
                    self.query[field] = value
        else:
            raise QueryException("Could not add filter %s! Check the database." % filter_name)

    def set_grouping(self, grouping):
        if grouping == "variant":
            self.grouped = True
            self.group_field = "variant"
        else:
            raise QueryException("Invalid grouping %s" % grouping)

    def get_query_only(self):
        return json_util.dumps(self.query)

    def execute(self):
        """
        Run a query and return # of rows returned
        """
        if not self.grouped:
            if len(self.query) == 0:
                self.data = g.conn["test"].variants\
                    .find(spec=self.query, fields=self.projection)\
                    .skip(self.skip)\
                    .limit(self.limit)
            else:
                self.data = g.conn["test"].variants.find(spec=self.query, fields=self.projection)\
                    .skip(self.skip)\
                    .limit(self.limit)\
                    .sort([("chrom", 1), ("start", 1)])\

        elif self.group_field == "variant":
            pipeline = []
            pipeline.append({"$match": self.query})
            pipeline.append({"$group":
                                {"_id":
                                    {"chrom": "$chrom",
                                     "start": "$start",
                                     "end": "$end",
                                     "id": "$id",
                                     "ref": "$ref",
                                     "alt": "$alt",
                                     },
                                 "count":
                                    {"$sum": 1},
                                 "annotations_list":
                                    {"$addToSet": "$annotations.EFF"},
                                 "sample_name_list":
                                    {"$addToSet": "$sample_name"},
                                 "filter":
                                    {"$addToSet": "$filter"}
                                }
                            })

            pipeline.append({"$project":
                                {"_id":
                                    {"$add": [0]},  # this is a stupid hack to put a literal/static field in
                                 "chrom": "$_id.chrom",
                                 "start": "$_id.start",
                                 "end": "$_id.end",
                                 "ref": "$_id.ref",
                                 "alt": "$_id.alt",
                                 "id": "$_id.id",
                                 "count": "$count",
                                 "annotations": "$annotations_list",
                                 "sample_name": "$sample_name_list",
                                 "filter": "$filter"
                                }
                            })
            pipeline.append({"$sort": {"chrom": 1, "start": 1}})

            self.data = self.var_mgr.documents.aggregate(pipeline)["result"]
        else:
            raise QueryException("Invalid grouping field %s in run_query!" % self.group_field)

    def get_results(self, format):
        """
        Return formatted results from query
        """
        self.out = {}
        if format == 'datatables':
            return self.format_datatables()
        elif format == 'csv':
            pass
        elif format == 'json':
            pass
        else:
            raise QueryException("Format %s not supported!" % format)

    def format_datatables(self):
        out = {}
        out["aaData"] = []
        for row in self.data:
            if self.grouped:
                row["annotations"] = {"EFF": row["annotations"][0]}
                row["filter"] = row["filter"][0]
                row["sample_name"] = int(row["count"])  # ", ".join(row["sample_name"])

            row_data = [row.get(c, '') for c in self.column_list]
            row_data.append("".join(["<div class='filter-tag %s'></div>" % f for f in row["filter"]]))
                
            highest_rank = 0
            effect_str = ""
            gene_str = ""

            for eff in row["annotations"].get("EFF", []):
                eff_code = eff.get("e", None)
                eff_type = VARIANT_EFFECTS[eff_code]
                eff_rank = VARIANT_RANKS[eff_type]
                if eff_rank > highest_rank:
                    eff_gene = eff.get("g", None)
                    if (eff_type in ["high", "moderate", "low"]) and (eff_gene is not None):
                        gene_str = eff_gene
                        effect_str = "<span class='label impact-tag %s'>%s</span>" % (eff_type, VARIANT_SHORTNAMES[eff_code])

            row_data.append(gene_str)
            if self.grouped:
                if row["end"] is not None:
                    pos_str = '%s:%d-%d' % (row["chrom"], row["start"], row["end"])
                else:
                    pos_str = '%s:%d' % (row["chrom"], row["start"])
                row_data.append("<a href='/variants/id:%s'>%s</a>" % (pos_str, effect_str))
                #row_data.append("<a href='/variants/id:%s'>id</a>" % (pos_str))
            else:
                row_data.append("<a href='/genotypes/id:%s'>%s</a>" % (row["_id"], effect_str))
                #row_data.append("<a href='/genotypes/id:%s'>id</a>" % row["_id"])

            for c in self.custom_column_list:
                if len(c) == 1:
                    row_data.append(row.get(c[0], ''))
                else:
                    if c[1] == "EFF":
                        try:
                            val = row[c[0]][c[1]][0].get(c[2], '')
                            row_data.append(val)
                        except KeyError:
                            row_data.append('')
                    elif c[1] == "dbNSFP":
                        try:
                            val = row[c[0]][c[1]].get(c[2], '')
                            row_data.append(val)
                        except KeyError:
                            row_data.append('')

            out["aaData"].append(row_data)
        return jsonify(out)
