import time

def retry(times=8, delay_s=1.0):
    def deco(fn):
        def wrapped(*a, **kw):
            last = None
            for _ in range(times):
                ok, val = fn(*a, **kw)
                if ok: return val
                last = val
                time.sleep(delay_s)
            return last
        return wrapped
    return deco
