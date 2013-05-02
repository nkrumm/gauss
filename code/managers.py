from pymongo import MongoClient
from mongokit import *
from orm_schema import *


class db_conn(object):
    """
    Class to provide low-level interface to database which abstracts
    connecting, queries and other stats
    """
    def __init__(self, host=None, user=None, password=None):
        self.conn = self.connect()
    def __del__(self):
        self.conn.disconnect()

    def connect(self, host=None, user=None, password=None):
        """
        Connect to MongoDB or other DB instance(s)
        """
        return MongoClient()
        


class manager_template(object):
    """
    Template for ORM insertion/selection methods
    """
    def __init__(self, db, conn, collection, doctype):
        conn.register([doctype])
        self.doctype = getattr(conn[db][collection], doctype.__name__)
        self.documents = self.conn[self.db][self.collection]

    def new_document(self):
        return self.doctype()

    def get(self, **kwargs):
        pass

    def insert(self, document):
        document.save()        


class sample_manager(manager_template):
    collection = "samples"
    document_type = Sample

    def __init__(self, db, conn):
        self.db = db
        self.conn = conn
        super(sample_manager, self).__init__(
            db=self.db,
            conn=self.conn,
            collection=self.collection,
            doctype=self.document_type)

    def get_sample(self, sample_id):
        """
        returns sample information. Performs necessary lookups of sample_id
        for synonym sample_ids
        """
        return self.documents.one({"identifier.sample_id": sample_id})

    def get_all_samples(self, study_name=None, study_id=None):
        """
        return the list of all samples.
        Optional study_name and study_id specifies which study to pull.
        """
        query = {}
        if study_name is not None:
            query["identifier.study_name"] = study_name
        if study_id is not None:
            query["identifier.study_id"] = study_id
        return self.documents.find(query, {"identifier.sample_id": True,"identifier.study_name": True, "attributes":True , "_id": False})

    def insert_sample(self, sample_id, study_id, study_name, files = None):
        """
        insert a new sample record. SampleID must be unique,
        but study_id can correspond to an existing collection
        """
        sample = self.new_document()
        sample.identifier.sample_id = sample_id
        sample.identifier.study_id = study_id
        sample.identifier.study_name = study_name
        if files is not None:
            sample.files = [files]
        self.insert(sample)

    def add_file_to_sample(self, sample_id, file_dict):
        self.documents.update({"identifier.sample_id":sample_id}, 
                              {"$push": {"files":file_dict}})


class study_manager(manager_template):
    collection = "studies"
    document_type = Study

    def __init__(self, db, conn):
        self.db = db
        self.conn = conn
        super(study_manager, self).__init__(
            db=self.db,
            conn=self.conn,
            collection=self.collection,
            doctype=self.document_type)

    def get_all_studies(self):
        """
        return the list of all studies.
        """
        return self.documents.find()

    def get_study(self, study_name):
        return self.documents.one({"study_name": study_name})

    def get_study_id(self, study_name):
        return self.documents.one({"study_name": study_name})["_id"]

    def insert_study(self, study_name, study_description=None):
        """
        insert a new study record.
        """
        study = self.new_document()
        study.study_name = study_name
        if study_description:
            study.study_description = study_description
        print study
        self.insert(study)


class variant_manager(manager_template):
    collection = "variants"
    document_type = Variant

    def __init__(self, db, conn):
        self.db = db
        self.conn = conn
        super(variant_manager, self).__init__(
            db=self.db,
            conn=self.conn,
            collection=self.collection,
            doctype=self.document_type)

    def insert_variant_from_vcf(self, sample_id, sample_name, chrom, pos, id, ref, alt, qual, filters, data, **annotations):
        """
        insert a new variant record based on VCF file
        All fields (except **annotations) required.
        'filter' should be a list of tags of valid Filter names
        """
        var = self.new_document()
        
        var.sample_id = sample_id
        var.sample_name = sample_name
        var.chrom = chrom
        var.start = pos
        if id is not None:
            var.id = id
        var.ref = ref
        var.alt = alt
        var.qual = qual
        if isinstance(filters, basestring):
            filters = [filters]
        var.filter = filters
        var.data = data
        var.annotations = {}
        for name,value in annotations.iteritems():
            var.annotations[name] = value
        
        self.insert(var)

    def get_variant(self, variant_id):
        return self.documents.find_one({"_id":ObjectId(variant_id)})

    def get_variants_by_gene(self, gene):
        return self.documents.find({"annotations.gene":gene})

    def get_variants_by_position(self, chrom, start, end=None, sort=True):
        if end is None:
            return self.documents.find({"chrom":str(chrom), "start": int(start)}).sort([("chrom", 1), ("start", 1)])
        if sort:
            return self.documents.find({"chrom":str(chrom), "start": {'$gte': int(start)}, "end": {'$lte': int(end)}}).sort([("chrom", 1), ("start", 1)])
        else:
            return self.documents.find({"chrom":str(chrom), "start": {'$gte': int(start)}, "end": {'$lte': int(end)}})

    def get_sample_variant_summary(self, sample_id):
        """
        return overview of variant counts for a sample
        """
        #data = self.documents.aggregate([{ "$match" : {"sample_id":ObjectId(sample_id)}} , {"$group" : {"_id": "$annotations.EFF.e",  "count": { "$sum": 1 } } }])
        data = self.documents.aggregate([{"$match":{"sample_id":ObjectId(sample_id)}},
                                         {"$unwind":"$annotations.EFF"},
                                         {"$group":{"_id": "$annotations.EFF.e", "count":{"$sum":1}}}])
        
        return data["result"]
        #out = {}
        #for row in data["result"]:
        #    out[row["_id"]] = row["count"]
        #return out



class filter_manager(manager_template):
    collection = "filters"
    document_type = Filter

    def __init__(self, db, conn):
        self.db = db
        self.conn = conn
        super(filter_manager, self).__init__(
            db=self.db,
            conn=self.conn,
            collection=self.collection,
            doctype=self.document_type)

    def get_all_filters(self):
        return self.documents.find({},{"_id":0,"date_added":0})

    def get_filter(self, filter_name):
        return self.documents.find({"filter_name": filter_name})

    def create_filter(self, filter_name, filter_description, prefix='in', filter_type='set', color='btn-warning'):
        filter_doc = self.new_document()
        filter_doc.filter_name = filter_name
        filter_doc.description = filter_description
        filter_doc.prefix = prefix
        filter_doc.type = filter_type
        filter_doc.color = color
        self.insert(filter_doc)
