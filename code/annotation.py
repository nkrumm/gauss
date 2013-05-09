import redis
from rq import Queue
import time


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

    def update(self, message=None):
        if message:
            self.notify_q.publish('chat', u'progress %s: %s' % (self.name, str(message)))
        else:
            self.progress_counter += 1
            self.notify_q.publish('chat', u'progress %s: %d' % (self.name, self.progress_counter))

    def start(self, args=None):
        self.notify_q = redis.Redis()
        self.notify_q.publish('chat', u'starting %s' % self.name)
        if args is not None:
            self.work(*args)
        else:
            self.work()
        self.notify_q.publish('chat', u'finished %s' % self.name)


class TestWorker(GaussWorker):
    def __init__(self, name=None):
        GaussWorker.__init__(self, name)

    def work(self, num):
        for i in xrange(num):
            self.update(i)
            print i
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


class GaussWorkerManager(object):
    def __init__(self):
        self.conn = redis.Redis()
        self.work_q = Queue(connection=self.conn)
        self.notify_q = self.conn
        self.registered_workers = []

    def register_worker(self, worker):
        self.registered_workers.append(worker)

    def get_registered_workers(self):
        return self.registered_workers

    def start_worker(self, worker, args=None):
        if worker in self.registered_workers:
            if args is not None:
                self.work_q.enqueue(worker.start, args)
            else:
                self.work_q.enqueue(worker.start)
        else:
            raise GaussWorkerException("Must register worker first!")

    def stop_worker(self, worker):
        raise NotImplementedException

    def get_worker_status(self, worker):
        raise NotImplementedException


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
