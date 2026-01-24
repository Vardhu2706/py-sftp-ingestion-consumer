import os


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


# SFTP
SFTP_HOST = require("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USERNAME = require("SFTP_USERNAME")
SFTP_PRIVATE_KEY_PATH = require("SFTP_PRIVATE_KEY_PATH")
SFTP_REMOTE_DIR = require("SFTP_REMOTE_DIR")  # Base directory, e.g., "upload"
SFTP_VENDORS = os.getenv("SFTP_VENDORS", "vendor_a,vendor_b,vendor_c,vendor_d").split(",")

# PGP
GPG_HOME = require("GPG_HOME")

# Consumer
DOWNLOAD_INTERVAL_SECONDS = int(os.getenv("DOWNLOAD_INTERVAL_SECONDS", "5"))