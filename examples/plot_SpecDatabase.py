"""
================================================
Spectrum Database
================================================
RADIS has :py:class:`~radis.tools.database.SpecDatabase` feature used to store and retrieve calculated Spectrums. A path can be specified for SpecDatabase all Spectrums are stored as .spec files which can be loaded
from the SpecDatabase object itself.  A csv file is generated which contains all input and conditional parameters of Spectrum.

RADIS also has :py:meth:`~radis.lbl.loader.DatabankLoader.init_database` feature which initializes the SpecDatabase for the SpectrumFactory and every Spectrum
generated from it will be stored in the SpecDatabase automatically.

You can use :py:meth:`~radis.tools.database.SpecList.plot_cond` to make a 2D plot using the conditions of the Spectrums in the SpecDatabase and use a z_label to plot a heat map based on it.


"""

import os

import numpy as np

from radis import SpectrumFactory
from radis.tools import SpecDatabase

sf = SpectrumFactory(
    wavenum_min=2900,
    wavenum_max=3200,
    molecule="OH",
    broadening_max_width=10,  # cm-1
    medium="vacuum",
    verbose=0,  # more for more details
    pressure=10,
    wstep=0.1,
)
sf.warnings = {"AccuracyError": "ignore"}
sf.fetch_databank("hitemp")

# Generating a Spectrum
s1 = sf.eq_spectrum(Tgas=300, path_length=1)

# Creating SpecDatabase
my_folder = os.getcwd() + "/SpecDatabase_Test"
db = SpecDatabase(my_folder)

# Method 1: Creating .spec file and adding manually to SpecDatabase
db.add(s1)

# Method 2: Using init_database()
# Generated Spectrum are added to SpecDatabase automatically
sf.init_database(my_folder)

wstep = np.linspace(0.1, 0.001, 4)
Tgas = np.linspace(300, 3000, 4)


# Multiple Spectrum calculation based on different values of Tgas and wstep
for i in wstep:
    sf.wstep = i
    sf.params.wstep = i
    for j in Tgas:
        sf.eq_spectrum(Tgas=j, path_length=1)


# Loading SpecDatabase
db_new = SpecDatabase(my_folder)

# Plot Tgas vs wstep for all Spectrums, heatmap based on calculation_time
db_new.plot_cond("Tgas", "wstep", "calculation_time")
