import multiprocessing

workers = multiprocessing.cpu_count()
bind = "0.0.0.0:8001"
keepalive = 120
errorlog = "-"
loglevel = "error"
