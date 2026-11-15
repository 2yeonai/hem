"""Bounded Linux worker; terminate on deadline, no database connection in child."""
import multiprocessing
import os


def _run(pipe, fn):
    try:
        pipe.send(('ok', fn()))
    except Exception:
        pipe.send(('error', None))
    finally:
        pipe.close()


def bounded(fn):
    seconds = max(.05, min(float(os.environ.get('AI_REQUEST_TIMEOUT_SECONDS', '45')), 120))
    ctx = multiprocessing.get_context('fork')
    receiver, sender = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_run, args=(sender, fn), daemon=True)
    process.start()
    sender.close()
    try:
        if not receiver.poll(seconds):
            raise TimeoutError('AI request deadline exceeded')
        status, result = receiver.recv()
        if status != 'ok': raise ValueError('AI analysis failed')
        return result
    finally:
        receiver.close()
        if process.is_alive(): process.terminate()
        process.join(timeout=1)
        if process.is_alive(): process.kill(); process.join()
