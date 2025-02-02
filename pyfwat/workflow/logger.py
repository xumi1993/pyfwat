import logging


class SetupLog(object):
    default_level = {
        0: logging.DEBUG,
        1: logging.INFO,
    }
    
    def __init__(self, filename='pyfwat.log', action='w', level=1):
        """
        use default_logs to gen loggers
        change default_logs for future changes if needed,
        check logger level with logger.getEffectiveLevel

        """
        self.default_logs = {
            "mesh": ("mesh", self.default_level[level], "file_handler", "stream_handler"),
            "forward": ("forward", self.default_level[level], "file_handler", "stream_handler"),
            "preproc": ("preproc", self.default_level[level], "file_handler", "stream_handler"),
            "adjoint": ("adjoint", self.default_level[level], "file_handler", "stream_handler"),
            "postproc": ("postproc", self.default_level[level], "file_handler", "stream_handler"),
            "optimize": ("optimize", self.default_level[level], "file_handler", "stream_handler"),
            "monitor": ("monitor", self.default_level[level], "file_handler", "stream_handler"),
        }
        self.filename = filename
        fh = logging.FileHandler(filename, mode=action)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        for loger_branch, config in self.default_logs.items():
            # init, setlevel
            log = logging.getLogger(config[0])
            log.setLevel(config[1])

            # add handler
            if not log.hasHandlers():
                if "file_handler" in config:
                    log.addHandler(fh)
                if "stream_handler" in config:
                    log.addHandler(ch)

            # attach to class
            setattr(self,loger_branch,log)


logger = SetupLog()
