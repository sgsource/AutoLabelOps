from PySide6.QtCore import QThread, Signal

class WorkerThread(QThread):
    """Generic worker thread for any callable with signals for status, result, and errors."""
    finished = Signal(object)  # emits result of function
    error = Signal(str)        # emits error message
    status = Signal(str)       # emits intermediate status updates

    def __init__(self, func, *args, **kwargs):
        """
        func: callable to run in thread
        *args, **kwargs: passed to func
        Optional special kwarg 'status_callback' can be passed to func to emit status messages.
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # If the function accepts a 'status_callback' kwarg, inject self.status.emit
            if 'status_callback' in self.kwargs:
                self.kwargs['status_callback'] = self.status.emit
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
