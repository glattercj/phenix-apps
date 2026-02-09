import json
import os
import stat
import sys
import traceback

from loguru import logger

import phenix_apps.common.settings as settings

# Define a format that includes colors and detailed location information
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def format_json_log(record: dict, message: str = None) -> str:
    """
    Formats the log record as a JSON string with 'level' and 'msg' keys
    to satisfy the Phenix orchestrator's logging requirements.

    The orchestrator (plog) reads the named pipe line-by-line. If a line is valid JSON,
    it attempts to parse 'level' and 'msg' fields to integrate the log entry into the
    system log with the correct severity. It also looks for a 'time' field (Unix microseconds)
    to preserve the original timestamp.
    """
    try:
        level = record["level"].name
        if level == "WARNING":
            level = "WARN"
        elif level == "CRITICAL":
            level = "ERROR"

        msg_content = message if message is not None else record["message"]
        final_msg = f"{record['name']}:{record['function']}:{record['line']} - {msg_content}"

        log_record = {
            "level": level,
            "msg": final_msg,
        }
        for k, v in record["extra"].items():
            if k not in log_record:
                log_record[k] = v

        if record["exception"]:
            exc = record["exception"]
            log_record["exception"] = "".join(traceback.format_exception(exc.type, exc.value, exc.traceback))
        return json.dumps(log_record, default=str) + "\n"
    except Exception as e:
        # Fallback to a simple error message if formatting fails
        return json.dumps({"level": "ERROR", "msg": f"JSON formatting error: {e}"}) + "\n"

def configure_logging(force_console: bool = False) -> None:
    """Configures the logger based on settings."""
    logger.remove()

    # Fetch log level directly from environment to ensure it's up-to-date
    log_level = os.getenv("PHENIX_LOG_LEVEL", settings.PHENIX_LOG_LEVEL).upper()
    if not log_level:
        log_level = "INFO"

    # Fetch log file from env to ensure we have the pipe path passed by user.go
    log_file = os.getenv("PHENIX_LOG_FILE", settings.PHENIX_LOG_FILE)

    # Check if the log file is a special stream (stdout/stderr)
    is_stream_log = log_file and (
        log_file in ["/dev/stdout", "/dev/stderr"] or log_file.startswith("/dev/fd/")
    )

    # If a log file is configured and it's not a standard stream, treat it as a pipe/file
    # that requires direct writing. This bypasses loguru's rotation/seeking logic which
    # crashes on named pipes (OSError: [Errno 29] Illegal seek).
    #
    # The Phenix orchestrator creates a named pipe for the app to write logs to.
    # Loguru's standard FileSink tries to stat/seek the file for rotation, which fails on pipes.
    if log_file and not is_stream_log:
        try:
            # Open pipe/file immediately with line buffering (buffering=1).
            # This ensures that log messages are flushed to the pipe immediately,
            # preventing them from being held in a buffer and lost if the app crashes
            # or if the orchestrator is waiting for output.
            pipe_stream = open(log_file, "w", encoding="utf-8", buffering=1)

            def sink(message):
                try:
                    # Format JSON here to avoid loguru formatting issues.
                    # We pass the formatted message string (message.record["message"] is the raw format string,
                    # message is the interpolated string) to be used in the JSON 'msg' field.
                    # This ensures that loguru's interpolation (e.g. logger.info("Value: {}", v)) works
                    # before we wrap it in JSON.
                    json_output = format_json_log(message.record, message)
                    pipe_stream.write(json_output)
                    pipe_stream.flush()
                except Exception:
                    pass

            logger.add(
                sink,
                level=log_level,
                # We use a simple format string here because the actual formatting happens inside the sink.
                # This tells loguru to just pass the interpolated message to the sink.
                format="{message}",
                catch=True,
            )
            return
        except Exception as e:
            sys.stderr.write(f"ERROR: Failed to open log pipe {log_file}: {e}\n")
            # Fall through to stderr logging if file open fails

    # Add stderr handler ONLY if we are forcing console OR if no log file is configured.
    # This prevents double logging when running under the orchestrator (which captures stderr).
    if force_console or not log_file:
        logger.add(
            sys.stderr,
            level=log_level,
            format=LOG_FORMAT,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
