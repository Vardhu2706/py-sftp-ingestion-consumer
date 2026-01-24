from flask import Flask, jsonify
from app.state_reader import StateReader
from app.logger import setup_logger

logger = setup_logger()
app = Flask(__name__)
state = StateReader()


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# Could be a problem - too many files possible
@app.route("/state")
def state_view():
    return jsonify(state.all_files())


if __name__ == "__main__":
    logger.info("Starting consumer-api")
    app.run(host="0.0.0.0", port=5000)