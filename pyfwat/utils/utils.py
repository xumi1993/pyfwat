from posixpath import dirname
import numpy as np
import subprocess
from os.path import join, basename, abspath
import re
import sys

def parse_cpt_name(cpt_name):
    cpt_path = join(dirname(abspath(__file__)), 'cpt', cpt_name+'.cpt')
    return cpt_path


class Dict(dict):
    """
    A dictionary replacement which allows for easier parameter access through
    getting and setting attributes. Also has some functionality to make string
    printing prettier
    """
    def __str__(self):
        """Pretty print dictionaries and first level nested dictionaries"""
        str_ = ""
        try:
            longest_key = max([len(_) for _ in self.keys()])
            for key, val in self.items():
                str_ += f"{key:<{longest_key}}: {val}\n"
        except ValueError:
            pass
        return str_

    def __repr__(self):
        """Pretty print when calling an instance of this object"""
        return self.__str__()

    def __getattr__(self, key):
        """Attribute-like access of the internal dictionary attributes"""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"{key} not found in Dict")

    def __setattr__(self, key, val):
        """Setting attributes can only be performed one time"""
        self.__dict__[key] = val
