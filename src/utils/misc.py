import inspect
from datetime import datetime
import csv
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, Iterable, Mapping, Union, Callable
import warnings

def now2str():
    now = datetime.now()
    now_str = now.strftime("%Y%m%d-%H%M%S")
    return now_str

def print_mro(x, print_fn:Callable=print):
    """
    Get the MRO of either a class x or an instance x
    """
    if inspect.isclass(x):
        [print_fn(kls) for kls in x.mro()[::-1]]
    else:
        [print_fn(kls) for kls in x.__class__.mro()[::-1]]

def mkdir(p: Path, parents=True):
    if not p.exists():
        p.mkdir(parents=parents)
        print("Created: ", p)

def write_record(record: Dict,
                 fp: Union[Path, str],
                 fieldnames: Optional[List[str]] = None,
                 verbose: bool = False):
    if fieldnames is None:
        fieldnames = list(record.keys())

    with open(fp, 'w') as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([
            record
        ])

    if verbose:
        print('\tWrote a record to csv file: ', fp)