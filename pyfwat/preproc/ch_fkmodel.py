"""Change a parameter in every ``src_rec/FKmodel_*`` file.

Command-line tool: ``fwat_ch_fkmodel``.
"""

from ..utils.pario import chpar
import glob
import argparse

def chfkmodel(key, value):
    """Set a parameter to the same value in every ``src_rec/FKmodel_*``.

    :param key: Parameter name, e.g. ``TAKE_OFF``
    :type key: str
    :param value: New value
    :type value: str or float
    """
    for fname in glob.glob('src_rec/FKmodel_*'):
        with open(fname) as f:
            fkpar = f.read()
        fkpar = chpar(fkpar, key=key, value=value, type='fk')
        with open(fname, 'w') as f:
            f.write(fkpar)


def main():
    """Command-line entry point of ``fwat_ch_fkmodel``."""
    parser = argparse.ArgumentParser('Batch change parameter in FKmodel')
    parser.add_argument('key', help='Key of parameter')
    parser.add_argument('value', help='Value of parameter')
    args = parser.parse_args()
    chfkmodel(args.key, args.value)
