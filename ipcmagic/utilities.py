import sys
import time
from IPython.display import clear_output


def watch_asyncresult(ar, dt=1, truncate=1000):
    """Watch the output of a non-blocking execution after or while
    it's running.
    Example (`tf.keras` training):
    ```
    In[1]:  %%px --noblock -o training
            fit = model.fit(dataset, callbacks=[initial_sync, history])

    Out[1]: <AsyncResult: execute>


    In[2]:  utilities.watch_asyncresult_log(training)

    Out[2]: [ stdout 0 ]
            673/1500 [============>.................] - ETA: 6s - loss: 0.0894
            [ stdout 1 ]
            673/1500 [============>.................] - ETA: 6s - loss: 0.0940
    ```
    """
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

    clear_output(wait=True)
    for eid, stdout in zip(ar._targets, ar.stdout):
        if stdout:
            print(f"[ stdout {eid} ]")
            print(f"{stdout[-truncate:]}")

    if 'error' in ar.status or None in ar.status:
        ar.display_outputs()


class Arguments:
    """Utility class to treat the magic class docopt args
    as class attribute instead of dictionary keys.
    self.args['option'] -> self.args.option
    """
    def __init__(self, attr_dict):
        if type(attr_dict) is dict:
            # replace `-` characters inside the string
            # like `num-engines` for instance
            attr_dict = {key.replace('-', '_'): val
                         for key, val in attr_dict.items()}
            self.__dict__.update(attr_dict)
