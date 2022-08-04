from ..pario import chpar
import glob
import argparse

def chfkmodel(key, value):
    for fname in glob.glob('src_rec/FKmodel_*'):
        with open(fname) as f:
            fkpar = f.read()
        fkpar = chpar(fkpar, key=key, value=value, type='fk')
        with open(fname, 'w') as f:
            f.write(fkpar)


def main():
    parser = argparse.ArgumentParser('Batch change parameter in FKmodel')
    parser.add_argument('key', help='Key of parameter')
    parser.add_argument('value', help='Value of parameter')
    args = parser.parse_args()
    chfkmodel(args.key, args.value)