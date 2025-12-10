"""Gunicorn configuration for running Flask app with Discord bot."""

from dotenv import load_dotenv
from flask.app import Flask

assert load_dotenv(), "Environment variables loaded"

bind = "0.0.0.0:8000"
workers = 1
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

reload = True


# Server hooks
def on_starting(_server: Flask):
    """Called just before the master process is initialized."""
    print("Gunicorn server is starting up...")


def on_exit(_server: Flask):
    """Called just before exiting."""
    print("Gunicorn server is shutting down...")
