from PySide6.QtCore import QObject, Signal, QSemaphore, QThread
from PySide6.QtCore import QTimer

class MultiWorkerManager(QObject):
    all_done = Signal(list)  # emits list of results

    def __init__(self, worker_tuples, status_logger, final_callback=None, per_result_callback=None):
        """
        worker_tuples: list of (WorkerThread, name) pairs
        status_logger: callable(str)
        final_callback: callable(results), called when all done
        per_result_callback: callable(result), called one-by-one after each result (serially)
        """
        super().__init__()
        self.workers = [w for w, _ in worker_tuples]
        self.names = [n for _, n in worker_tuples]
        self.status_logger = status_logger
        self.final_callback = final_callback
        self.per_result_callback = per_result_callback
        self.results = [None] * len(self.workers)
        self.finished_count = 0

        self.semaphore = QSemaphore(1)  # Only one post-process at a time

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

        # Start serialized per-result post-processing in a separate thread
        if self.per_result_callback:
            post_thread = QThread()
            worker = PostProcessor(result, self.per_result_callback, self.semaphore)
            worker.moveToThread(post_thread)

            post_thread.started.connect(worker.run)
            worker.finished.connect(post_thread.quit)
            worker.finished.connect(worker.deleteLater)
            post_thread.finished.connect(post_thread.deleteLater)

            post_thread.start()

        # If all done, emit final callback
        if self.finished_count == len(self.workers):
            if self.final_callback:
                self.final_callback(self.results)
            self.all_done.emit(self.results)


class PostProcessor(QObject):
    finished = Signal()

    def __init__(self, result, callback, semaphore):
        super().__init__()
        self.result = result
        self.callback = callback
        self.semaphore = semaphore

    def run(self):
        self.semaphore.acquire()
        try:
            self.callback(self.result)
        finally:
            self.semaphore.release()
            self.finished.emit()
