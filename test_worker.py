import annotation
from rq import Connection, Queue
import redis

manager = annotation.GaussWorkerManager()

worker = annotation.GeneAnnotationWorker2("mygeneworker")

manager.register_worker(worker)
manager.start_worker(worker,
                     args=("testfilter",
                           "/Users/nkrumm/cuttlefish/gauss/Gene_file.test.txt"))

print manager.get_registered_workers()
