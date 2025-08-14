# Gunicorn configuration for Video and Audio Subtitle Generator

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 300  # 5 minutes for large file uploads
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "subtitle_generator"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Preload app for better performance
preload_app = True

# Maximum size of HTTP request line in bytes
limit_request_line = 4094

# Maximum number of HTTP request header fields
limit_request_fields = 100

# Maximum size of HTTP request header field
limit_request_field_size = 8190