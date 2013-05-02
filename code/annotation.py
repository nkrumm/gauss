

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
