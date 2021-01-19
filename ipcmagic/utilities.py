import sys
import time
from IPython.display import clear_output


def watch_asyncresult_log(ar, dt=1, truncate=1000):
    while not ar.ready():
        stdouts = ar.stdout
        if not any(stdouts):
            continue

        clear_output(wait=True)
        for eid, stdout in zip(ar._targets, ar.stdout):
            if stdout:
                print(f"[ stdout {eid} ]")
                print(f"{stdout[-truncate:]}")

        sys.stdout.flush()
        time.sleep(dt)

    if all(i == 'ok' for i in ar.status):
        clear_output(wait=True)
        for eid, stdout in zip(ar._targets, ar.stdout):
            if stdout:
                print(f"[ stdout {eid} ]")
                print(f"{stdout[-truncate:]}")
    else:  # 'error' or None in ar.status
        ar.display_outputs()
