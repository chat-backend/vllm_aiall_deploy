# gunicorn.conf.py
# AIALL Gateway – Production Gunicorn Configuration

import multiprocessing
import os

# ================================
#  Server Binding
# ================================
bind = "0.0.0.0:5000"

# ================================
#  Worker Settings
# ================================
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 2000

max_requests = 2000
max_requests_jitter = 200

# ================================
#  Performance Tuning
# ================================
timeout = 120
graceful_timeout = 30
keepalive = 5

# Tối ưu I/O
worker_tmp_dir = "/dev/shm"

# ================================
#  Logging
# ================================
loglevel = "info"
accesslog = "/var/log/aiall-gateway-access.log"
errorlog = "/var/log/aiall-gateway-error.log"
capture_output = True

access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s"'
)

# ================================
#  Security Hardening
# ================================
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
limit_request_body = 16 * 1024 * 1024

# Cho phép Nginx forward IP client
forwarded_allow_ips = "*"

# ================================
#  Reload (Dev Mode)
# ================================
reload = os.getenv("APP_ENV") == "development"

# ================================
#  Preload App
# ================================
preload_app = True

