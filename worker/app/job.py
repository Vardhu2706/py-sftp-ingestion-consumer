from app.ai.interpreter import AIInterpreter
from app.persistance import persist
from app.logger import setup_logger


logger = setup_logger()
ai = AIInterpreter()

def ai_interpret_job(payload: str):
    """
    payload = {
        "filename": str,
        "text": str
    }
    """
    filename = payload["filename"]
    text = payload["text"]

    logger.info(f"AI JOB START | {filename}")

    result = ai.interpret(text)
    persist(result, filename)

    logger.info(f"AI JOB DONE | {filename}")
    return result