from flask import Flask, jsonify, request
from app.state_reader import StateReader
from app.logger import setup_logger
import redis
from rq import Queue

logger = setup_logger()
app = Flask(__name__)
state = StateReader()

# Redis connection for queue status
try:
    redis_conn = redis.Redis(host="localhost", port=6379)
    ai_queue = Queue("ai", connection=redis_conn)
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    redis_conn = None
    ai_queue = None


@app.route("/health")
def health():
    """Health check endpoint."""
    health_status = {
        "status": "ok",
        "database": "ok"
    }
    
    # Check database connection
    try:
        state.all_files(limit=1)
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = "error"
        health_status["database_error"] = str(e)
    
    # Check Redis connection
    if redis_conn:
        try:
            redis_conn.ping()
            health_status["redis"] = "ok"
        except Exception as e:
            health_status["redis"] = "error"
            health_status["redis_error"] = str(e)
    else:
        health_status["redis"] = "not_configured"
    
    status_code = 200 if health_status["status"] == "ok" else 503
    return jsonify(health_status), status_code


@app.route("/state")
def state_view():
    """
    Get file processing states with optional filtering and pagination.
    
    Query parameters:
    - limit: Number of results (default: 100, max: 1000)
    - offset: Pagination offset (default: 0)
    - state: Filter by state (CLAIMED, PROCESSING, DONE, FAILED, RETRYABLE_FAILED)
    - vendor: Filter by vendor (e.g., vendor_a)
    """
    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        state_filter = request.args.get("state", type=str)
        vendor = request.args.get("vendor", type=str)
        
        # Cap limit to prevent performance issues
        limit = min(limit, 1000)
        
        files = state.all_files(
            limit=limit,
            offset=offset,
            state=state_filter,
            vendor=vendor
        )
        
        return jsonify({
            "files": files,
            "count": len(files),
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        logger.error(f"Error in state_view: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/state/<filename>")
def file_detail(filename: str):
    """Get detailed information about a specific file."""
    try:
        file_info = state.get_file(filename)
        if not file_info:
            return jsonify({"error": "File not found"}), 404
        return jsonify(file_info)
    except Exception as e:
        logger.error(f"Error in file_detail: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/stats")
def stats():
    """Get aggregate statistics about file processing."""
    try:
        stats_data = state.get_stats()
        return jsonify(stats_data)
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/search")
def search():
    """
    Search files by filename.
    
    Query parameters:
    - q: Search query (required)
    - limit: Number of results (default: 50, max: 100)
    """
    try:
        query = request.args.get("q", type=str)
        if not query:
            return jsonify({"error": "Query parameter 'q' is required"}), 400
        
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 100)
        
        results = state.search_files(query, limit=limit)
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue")
def queue_status():
    """Get Redis queue status and job counts."""
    if not ai_queue:
        return jsonify({"error": "Redis queue not available"}), 503
    
    try:
        queue_length = len(ai_queue)
        
        # Get job registry counts
        started_jobs = len(ai_queue.started_job_registry)
        finished_jobs = len(ai_queue.finished_job_registry)
        failed_jobs = len(ai_queue.failed_job_registry)
        
        return jsonify({
            "queue": "ai",
            "queued": queue_length,
            "started": started_jobs,
            "finished": finished_jobs,
            "failed": failed_jobs
        })
    except Exception as e:
        logger.error(f"Error in queue_status: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting consumer-api")
    app.run(host="0.0.0.0", port=5000, debug=False)