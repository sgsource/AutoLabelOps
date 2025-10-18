from PySide6.QtCore import QObject, Signal

class MultiWorkerManager(QObject):
    all_done = Signal(list)  # emits list of results

    def __init__(self, worker_tuples, status_logger, final_callback=None):
        """
        worker_tuples: list of (WorkerThread, name) pairs
        status_logger: callable(str)
        final_callback: callable(results), called when all done
        """
        super().__init__()
        self.workers = [w for w, _ in worker_tuples]
        self.names = [n for _, n in worker_tuples]
        self.status_logger = status_logger
        self.final_callback = final_callback
        self.results = [None] * len(self.workers)
        self.finished_count = 0

        for idx, worker in enumerate(self.workers):
            name = self.names[idx]
            worker.status.connect(lambda msg, n=name: status_logger(f"[{n}] {msg}"))
            worker.finished.connect(lambda result, i=idx: self._worker_finished(i, result))
            worker.error.connect(lambda e, n=name: status_logger(f"[{n}] ERROR: {e}"))

    def start(self):
        for worker in self.workers:
            worker.start()

    def _worker_finished(self, index, result):
        self.results[index] = result
        self.finished_count += 1
        if self.finished_count == len(self.workers):
            if self.final_callback:
                self.final_callback(self.results)
            self.all_done.emit(self.results)
