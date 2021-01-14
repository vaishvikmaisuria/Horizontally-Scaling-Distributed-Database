import json
import multiprocessing

cores = multiprocessing.cpu_count()
workers_per_core = 2

# Gunicorn config variables
loglevel = "info"
workers = int(workers_per_core * cores)
threads = 5
bind = "0.0.0.0:80"
keepalive = 120
errorlog = "-"

# For debugging and testing
log_data = {
    "loglevel": loglevel,
    "workers": workers,
    "bind": bind,
    # Additional, non-gunicorn variables
    "workers_per_core": workers_per_core
}
print(json.dumps(log_data))