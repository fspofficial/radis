# -*- coding: utf-8 -*-
"""

::

                *(((((((
                 ((((((((((((              ,(((((
                 ((((((((((((((((/   *((((((((((*
                  ((((((((((((((((( ((((((((((((
                      (((((((( (((((((((((((
                         *
                       @@  *@@       ..  /@@
                  @@&  @@  *@@       @@  /@@  @@%
              @@  @@&  @@  *@@  @@&  @@  /@@  @@%  @@
              @@  @@&  @@  *@@  @@&  @@  /@@  @@%  @@
              @@  @@&  @@  *@@  @@&  @@  /@@  @@%  @@  (@
         ,@   @@  @@&  @@  *@@  @@&  @@  /@@  @@%  @@
         @@   @@  @@&  @@  ,.
                                    ,%&&&&&&&&&&&&&&&&&&&
          &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
           &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
             &&&&&&&&&&&&&&&&@@@@@@&@@@&&&@@@&&&&&&&&
               &&&&&&&&&&&&&&&@@@@@@&&&&&&&&&&&&&&&
                 &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
                   &&&&&&&&&&&&&&&&&&&&&&&&&&&.
                       &&&&&&&&&&&&&&&&&&&
                               .**.
                                &&&,
                                 &&

"""

import os

from .misc.config import get_config
from .misc.utils import Chdir as _chdir
from .misc.utils import getProjectRoot

# %% Config files

# @dev: refactor in progress.
# So far there are config files in ~/radis.json (for databanks), global variables
# here, and a radis/config.json file.
# Everything should be merged in a user JSON file ~/radis.json (json) overriding
# the default one.

config = get_config()
"""dict: RADIS configuration parameters

Notes
-----

refactor in progress.
So far there are config files in ~/radis.json (for databanks), global variables
here, and a radis/config.json file.
Everything should be merged in a user JSON file ~/radis.json (json) overriding
the default one.
"""


# %% Global constants
from .params import (
    AUTO_UPDATE_SPEC,
    DEBUG_MODE,
    GRIDPOINTS_PER_LINEWIDTH_ERROR_THRESHOLD,
    GRIDPOINTS_PER_LINEWIDTH_WARN_THRESHOLD,
    OLDEST_COMPATIBLE_VERSION,
    USE_CYTHON,
)

# %% Version


def get_version(verbose=False, add_git_number=True):
    """Reads `__version.txt__
    <https://github.com/radis/radis/blob/master/radis/__version__.txt>`__ and
    retrieve version number. If ``add_git_number``, also appends Git commit
    number if we're on a gitted session.

    Examples
    --------

    ::

        import radis
        print(radis.get_version())
        >>> '0.9.17'
    """

    # First get version
    with open(os.path.join(getProjectRoot(), "__version__.txt")) as version_file:
        version = version_file.read().strip()

    # Now get git info
    if add_git_number:
        import subprocess
        import sys

        cd = _chdir(os.path.dirname(__file__))
        try:
            label = subprocess.check_output("git describe", stderr=subprocess.DEVNULL)
        except:
            if verbose:
                print("couldnt get git version: {0}".format(sys.exc_info()[1]))
            # probably not a git session. drop
        else:
            commit = label.decode().strip().split("-")[-1]
            version = version + "-" + commit
        finally:
            cd.__del__()

    return version


__version__ = get_version(add_git_number=False)
version = get_version(add_git_number=False)


# %% Global namespace

__all__ = [
    "AUTO_UPDATE_SPEC",
    "DEBUG_MODE",
    "GRIDPOINTS_PER_LINEWIDTH_ERROR_THRESHOLD",
    "GRIDPOINTS_PER_LINEWIDTH_WARN_THRESHOLD",
    "OLDEST_COMPATIBLE_VERSION",
    "USE_CYTHON",
    "version",
    "__version__",
]

# prevent cyclic importants:
from . import db, io, lbl, los, misc, phys, spectrum, tools
from .db import *  # database of molecules
from .io import *  # input / output
from .lbl import *  # line-by-line module
from .levels import *  # rovibrational energies and partition functions
from .los import *  # line-of-sight module
from .phys import *  # conversion functions, blackbody objects
from .spectrum import *  # Spectrum object
from .test import *  # test
from .tools import *  # slit, database, line survey, etc.

__all__.extend(db.__all__)
__all__.extend(io.__all__)
__all__.extend(lbl.__all__)
__all__.extend(los.__all__)
__all__.extend(phys.__all__)
__all__.extend(spectrum.__all__)
__all__.extend(tools.__all__)
