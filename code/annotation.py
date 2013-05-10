import redis
from rq import Queue, get_current_job
import time
from managers import manager_template, db_conn
from orm_schema import Job
from pymongo import MongoClient

class GaussWorkerException(Exception):
    pass


class NotImplementedException(Exception):
    pass


class GaussWorker(object):
    def __init__(self, name=None):
        if name is not None:
            self.name = name
        else:
            self.name = "randomstring"
        self.progress_counter = 0
        self.mongodb_id = None
    
    def update_status(self, status=None):
        if status is not None:
            self.conn["test"].jobs.update({"_id": self.mongodb_id},  {"$set": {"status": status}})
            self.notify_q.publish('chat', u'update %s' % status)
            print "setting status to ", status
        else:
            pass

    def start(self, args=None):
        self.conn = MongoClient()
        self.notify_q = redis.Redis()
        self.update_status("Started")
        print args
        if args is not None:
            self.work(*args)
        else:
            self.work()
        self.update_status("Completed")
        

class TestWorker(GaussWorker):
    def __init__(self, name=None):
        GaussWorker.__init__(self, name)

    def work(self, num):
        for i in xrange(num):
            print i
            self.update_status("Progress %d/%d" % (i,num))
            time.sleep(1)

class GeneAnnotationWorker2(GaussWorker):
    def __init__(self, name=None):
        GaussWorker.__init__(self, name)

    def work(self, filter_name, gene_file):  # , db, conn):
        genes = []
        with open(gene_file) as f:
            for line in f:
                g = line.strip("\n")
                genes.append(g)
                self.update()
        self.update("finished reading file list")
        # documents = conn[db]["variants"]
        # documents.update({"annotations.EFF.g": {"$in": genes}},
        #                  {"$push": {"filter": filter_name}},
        #                  {"multi": True})
        self.update("finished database update")


class GaussWorkerManager(manager_template):
    collection = "jobs"
    document_type = Job

    def __init__(self, db, conn):
        self.db = db
        self.conn = conn
        self.redis_conn = redis.Redis()
        self.work_q = Queue(connection=self.redis_conn)
        self.notify_q = self.redis_conn
        super(GaussWorkerManager, self).__init__(
            db=self.db,
            conn=self.conn,
            collection=self.collection,
            doctype=self.document_type)

        
        #self.registered_workers = []

    def register_worker(self, worker):
        #self.registered_workers.append(worker)
        pass
        
    def get_registered_workers(self):
        return self.registered_workers

    def start_worker(self, worker, args=None):
        job_doc = self.new_document()
        job_doc.job_name = worker.name
        job_doc.status = "created"
        _id = self.insert(job_doc)
        print "_id", _id
        worker.mongodb_id = _id
        if args is not None:
            job = self.work_q.enqueue(worker.start, args)
        else:
            job =  self.work_q.enqueue(worker.start)
        
        #print "Started job with job.id = %s, and mongodb_id = %s" % (job.id, _id)

    def stop_worker(self, worker):
        raise NotImplementedException

    def get_worker_status(self, worker):
        raise NotImplementedException

    def get_all_jobs(self):
        return self.documents.find().sort("date_registered", -1)



class GeneAnnotationWorker(object):
    def __init__(self, gene_file, db, conn):
        self.genes = []
        with open(gene_file) as f:
            for line in f:
                self.genes.append(line.strip("\n"))

        self.db = db
        self.documents = self.conn[self.db]["variants"]

    def start(self, filter_name):
        #self.register()
        #self.bam_file = loadbam()
        #do the annotation
        self.documents.update({"annotations.EFF.g": {"$in": self.genes}},
                              {"$push": {"filter": filter_name}},
                              {"multi": True})

    def end():
        #cleanup()
        #self.done()
        pass
