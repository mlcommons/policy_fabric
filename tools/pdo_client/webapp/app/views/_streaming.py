"""Reusable progress streaming for multi-step flows.

A flow (identity provisioning, asset registration, expose, use, ...) is a
sequence of high-level steps. These helpers turn such a flow into an NDJSON
``StreamingHttpResponse`` -- one JSON line per transition -- that the client's
``window.progress`` (static/js/progress.js) renders live in a modal.

Event line shape::

    {"step": "<id>", "status": "start|done|skip|error", "label": "...", "detail": "..."}

The stream always ends with one terminal line::

    {"step": "complete", "status": "done|error", "label": "Done", ...extra}

where ``extra`` (only on success) may carry e.g. ``{"redirect": "/"}`` or
``{"result": {...}}`` for the client to act on.

Two entry points:

* :func:`stream_steps` -- give it ``(id, label, fn)`` triples; it runs each
  ``fn(ctx)`` and emits start/done/skip/error around it. Best for a flow whose
  steps are plain function calls sharing a ``ctx`` dict.
* :func:`stream_events` -- give it a generator that already yields event dicts
  (e.g. one that interleaves its own logic). Best when the flow is easier to
  write by hand.
"""

import json
import logging

from django.http import StreamingHttpResponse

logger = logging.getLogger(__name__)


class SkipStep(Exception):
    """Raise inside a step body to mark that step skipped (a no-op), not failed.

    The message becomes the step's ``detail`` (e.g. "already exists").
    """


def make_event(step, status, label, detail=""):
    return {"step": step, "status": status, "label": label, "detail": detail}


def _finalize(errored, complete):
    """Build the terminal ``complete`` event, running ``complete`` (if given and
    the flow succeeded) to merge in extra fields like ``redirect``/``result``."""
    term = {"step": "complete", "status": "error" if errored else "done", "label": "Done"}
    if not errored and complete is not None:
        try:
            term.update(complete() or {})
        except Exception as e:
            logger.exception("flow completion callback failed")
            term = {"step": "complete", "status": "error", "label": "Done", "detail": str(e)}
    return term


def _response(body):
    resp = StreamingHttpResponse(body, content_type="application/x-ndjson")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # don't let a proxy buffer the stream
    return resp


def stream_events(events, *, complete=None, fatal=None):
    """Stream a ready-made iterable of event dicts, then a terminal event.

    ``complete`` is an optional zero-arg callable returning a dict merged into
    the terminal event (only when the flow succeeded).

    ``fatal(event)`` decides whether an errored step fails the whole flow; by
    default every error does. A flow whose parts can fail independently says so
    here — in a federated round, one site refusing is a result to report, not a
    breakdown, and the round still has numbers to show from everyone else.
    """
    def body():
        errored = False
        for event in events:
            if event.get("status") == "error" and (fatal is None or fatal(event)):
                errored = True
            yield json.dumps(event) + "\n"
        yield json.dumps(_finalize(errored, complete)) + "\n"

    return _response(body())


def stream_steps(steps, *, ctx=None, complete=None):
    """Run ``steps`` and stream progress, then a terminal event.

    ``steps`` is an iterable of ``(step_id, label, fn)``; ``fn(ctx)`` does the
    work and may return a dict merged into the shared ``ctx``. Raise
    :class:`SkipStep` to skip a step; any other exception marks it errored and
    aborts the remaining steps. ``complete(ctx)`` (optional) runs only on full
    success and returns extra terminal fields.
    """
    ctx = ctx if ctx is not None else {}

    def events():
        for step_id, label, fn in steps:
            yield make_event(step_id, "start", label)
            try:
                result = fn(ctx)
            except SkipStep as e:
                yield make_event(step_id, "skip", label, str(e))
                continue
            except Exception as e:
                logger.exception("flow step %r failed", step_id)
                yield make_event(step_id, "error", label, str(e))
                return  # abort the remaining steps
            if isinstance(result, dict):
                ctx.update(result)
            detail = result.get("detail", "") if isinstance(result, dict) else ""
            yield make_event(step_id, "done", label, detail)

    return stream_events(
        events(), complete=(lambda: complete(ctx)) if complete is not None else None
    )
