import io
import logging
import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import configure_application_logging  # noqa: E402


def test_mininode_namespace_enables_info_without_enabling_external_libraries():
    configure_application_logging()

    assert logging.getLogger("mininode_api.services.privacy_diagnostic").isEnabledFor(
        logging.INFO
    )
    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)


def test_application_logging_reuses_uvicorn_handler_without_duplication():
    application_logger = logging.getLogger("mininode_api")
    uvicorn_logger = logging.getLogger("uvicorn.error")
    uvicorn_parent_logger = logging.getLogger("uvicorn")
    original_application_handlers = application_logger.handlers[:]
    original_uvicorn_handlers = uvicorn_logger.handlers[:]
    original_uvicorn_parent_handlers = uvicorn_parent_logger.handlers[:]
    original_propagate = application_logger.propagate
    output = io.StringIO()
    handler = logging.StreamHandler(output)

    try:
        application_logger.handlers = []
        uvicorn_logger.handlers = []
        uvicorn_parent_logger.handlers = [handler]

        configure_application_logging()
        configure_application_logging()
        logging.getLogger("mininode_api.services.privacy_diagnostic").info(
            "privacy_adaptive_scope_completed"
        )

        assert application_logger.handlers == [handler]
        assert application_logger.propagate is False
        assert output.getvalue().count("privacy_adaptive_scope_completed") == 1
    finally:
        application_logger.handlers = original_application_handlers
        application_logger.propagate = original_propagate
        uvicorn_logger.handlers = original_uvicorn_handlers
        uvicorn_parent_logger.handlers = original_uvicorn_parent_handlers
