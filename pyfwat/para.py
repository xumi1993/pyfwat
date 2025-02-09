from ruamel.yaml import YAML
from pyfwat.utils.utils import Dict
import os


yaml = YAML()
yaml.default_flow_style = True

  
def str2val(str_val):
    """
    Convert string to int, float or list of int or float
    """
    try:
        return int(str_val)
    except ValueError:
        pass

    # return float
    try:
        return float(str_val)
    except ValueError:
        pass

    # list values handling
    # return list of integer
    try:
        return [int(v) for v in str_val.strip('[]').split(',')]
    except ValueError:
        pass

    # return list of float
    try:
        return [float(v) for v in str_val.strip('[]').split(',')]
    except ValueError:
        pass

    return str_val

class FWATPara(object):
    """
    Class to load, save and modify parameters for FWAT
    """
    def __init__(self, **kwargs):
        self.jobids = []
        self.exec = 'mpirun'
        self.slurm = Dict({
            "ntasks": None,
            "walltime": None,
            "args": None,
            "partition": None
        })
        self.path = Dict({
            "workdir": None,
            "logdir": None,
        })
        for key, value in kwargs.items():
            if hasattr(self, key):
                getattr(self, key).update(value)
            else:
                setattr(self, key, value)
        self._setup_force()
    
    def _setup_force(self):
        self.path['logdir'] = os.path.join(self.path.workdir, "logs")
        self.abs_workdir = os.path.abspath(self.path.workdir)

    @classmethod
    def read(cls, para_file):
        """
        Read parameters from a file
        """
        para_file = para_file
        with open(para_file, encoding='utf-8') as f:
            file_data = f.read()
        para = yaml.load(file_data)
        return cls(**para)

    def update_param(self, key: str, value) -> None:
        """
        Update a parameter based on a dot-separated key path.

        :param key: The key path separated by '.' to indicate nested keys.
        :type key: str
        :param value: The new value to set at the specified key.
        """
        keys = key.split('.')
        obj = self
        # Traverse until the second-to-last key
        for k in keys[:-1]:
            if not hasattr(obj, k):
                raise ValueError(f"Key {key} not found in FWATPara")
            obj = getattr(obj, k)

        # Update the target final key
        last_key = keys[-1]
        if isinstance(obj, dict):
            if last_key in obj:
                obj[last_key] = value
            else:
                raise ValueError(f"Key {last_key} not found in dictionary.")
        else:
            if hasattr(obj, last_key):
                setattr(obj, last_key, value)
            else:
                raise ValueError(f"Key {last_key} not found in FWATPara")

    def write(self, fname=None):
        """
        Write the parameters to a file

        :param fname: Path to output file, for None to overwrite input file, defaults to None
        :type fname: str, optional
        """
        if fname is None:
            fname = self.para_file
        with open(fname, 'w') as f:
            yaml.dump(self.para, f)

    def __str__(self) -> str:
        """
        Return a string representation of all parameters with proper indentation.
        """
        def format_attribute(name, value, indent=0):
            spaces = ' ' * indent
            if isinstance(value, dict):
                items = (f"{spaces}  {key}: {format_attribute('', val, indent + 2)}" for key, val in value.items())
                return f"{name}:\n" + "\n".join(items)
            else:
                return f"{spaces}{name} {value}" if name else f"{spaces}{value}"

        attributes = []
        for attr in dir(self):
            if attr.startswith('_') or callable(getattr(self, attr)):
                continue
            formatted = format_attribute(attr, getattr(self, attr), 0)
            attributes.append(formatted)
        return "\n".join(attributes)
  
if __name__ == '__main__':
    para = FWATPara.read(os.path.dirname(__file__) + '/data/fwat_params.yml')
    para.update_param('slurm.ntasks', 10)
    print(para.path['workdir'])
    print(getattr(para, 'noise')['set_name'])