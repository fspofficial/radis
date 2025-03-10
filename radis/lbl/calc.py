# -*- coding: utf-8 -*-
"""
Summary
-------

Public (front-end) functions to calculate Spectrum with HITRAN / CDSD databanks.
Uses the SpectrumFactory class from `factory.py`, Spectrum from `spectrum.py`
and line survey from `line_survey.py`

Routine Listing
---------------

:func:`~radis.lbl.calc.calc_spectrum`

-------------------------------------------------------------------------------

"""


from copy import deepcopy
from os.path import exists

try:  # Proper import
    from .labels import SpectrumFactory
except ImportError:  # if ran from here
    from radis.lbl.factory import SpectrumFactory
from radis.misc.basics import all_in
from radis.phys.air import air2vacuum
from radis.phys.convert import nm2cm
from radis.spectrum.spectrum import Spectrum


# %%
def calc_spectrum(
    wavenum_min=None,
    wavenum_max=None,
    wavelength_min=None,
    wavelength_max=None,
    Tgas=None,
    Tvib=None,
    Trot=None,
    pressure=1.01325,
    molecule=None,
    isotope="all",
    mole_fraction=1,
    path_length=1,
    databank="hitran",
    medium="air",
    wstep=0.01,
    broadening_max_width=10,
    cutoff=1e-27,
    parsum_mode="full summation",
    optimization="min-RMS",
    overpopulation=None,
    name=None,
    save_to="",
    use_cached=True,
    mode="cpu",
    export_lines=False,
    verbose=True,
    **kwargs
) -> Spectrum:
    r"""Multipurpose function to calculate a :py:class:`~radis.spectrum.spectrum.Spectrum`.

    Can automatically download databases (HITRAN/HITEMP) or use manually downloaded
    local databases, under equilibrium or non-equilibrium, with or without overpopulation,
    using either CPU or GPU.

    It is a wrapper to :py:class:`~radis.lbl.factory.SpectrumFactory` class.
    For advanced used, please refer to the aforementionned class.


    Parameters
    ----------
    wavenum_min, wavenum_max: float [:math:`cm^{-1}`] or `~astropy.units.quantity.Quantity`
        wavenumber range to be processed in :math:`cm^{-1}`. Use arbitrary units::

            import astropy.units as u
            calc_spectrum(2.5*u.um, 3.0*u.um, ...)

    wavelength_min, wavelength_max: float [:math:`nm`] or `~astropy.units.quantity.Quantity`
        wavelength range to be processed in :math:`nm`. Wavelength in ``'air'`` or
        ``'vacuum'`` depending of the value of ``'medium'``.
    Tgas: float [:math:`K`]
        Gas temperature. If non equilibrium, is used for :math:`T_{translational}`.
        Default ``300`` K​
    Tvib, Trot: float [:math:`K`]
        Vibrational and rotational temperatures (for non-LTE calculations).
        If ``None``, they are at equilibrium with ``Tgas`` ​.
    pressure: float [:math:`bar`] or `~astropy.units.quantity.Quantity`
        partial pressure of gas in bar. Default ``1.01325`` (1 atm)​. Use arbitrary units::

            import astropy.units as u
            calc_spectrum(..., pressure=20*u.mbar)

    molecule: int, str, list or ``None``
        molecule id (HITRAN format) or name. For multiple molecules, use a list.
        The ``'isotope'``, ``'mole_fraction'``, ``'databank'`` and ``'overpopulation'`` parameters must then
        be dictionaries.
        If ``None``, the molecule can be infered
        from the database files being loaded. See the list of supported molecules
        in :py:data:`~radis.db.MOLECULES_LIST_EQUILIBRIUM`
        and :py:data:`~radis.db.MOLECULES_LIST_NONEQUILIBRIUM`.
        Default ``None``.​
    isotope: int, list, str of the form ``'1,2'``, or ``'all'``, or dict
        isotope id (sorted by relative density: (eg: 1: CO2-626, 2: CO2-636 for CO2).
        See [HITRAN-2016]_ documentation for isotope list for all species. If ``'all'``,
        all isotopes in database are used (this may result in larger computation
        times!). Default ``'all'``.

        For multiple molecules, use a dictionary with molecule names as keys ::

            isotope={'CO2':'1,2' ,  'CO':'1,2,3' }​

    mole_fraction: float or dict
        database species mole fraction. Default ``1``.

        For multiple molecules, use a dictionary with molecule names as keys ::

            mole_fraction={'CO2': 0.8, 'CO':0.2}​

    path_length: float [:math:`cm`] or `~astropy.units.quantity.Quantity`
        slab size. Default ``1`` cm​. Use arbitrary units::

            import astropy.units as u
            calc_spectrum(..., path_length=1000*u.km)

    databank: str or dict
        can be either:
        - ``'hitran'``, to fetch automatically the latest HITRAN version
          through :py:func:`~radis.io.query.fetch_astroquery` (based on [HAPI]_ ).
        - ``'hitemp'``, to fetch automatically the latest HITEMP version
          through :py:func:`~radis.io.hitemp.fetch_hitemp`.
        - the name of a a valid database file, in which case the format is inferred.
          For instance, ``'.par'`` is recognized as ``hitran/hitemp`` format.
          Accepts wildcards ``'*'`` to select multiple files.
        - the name of a spectral database registered in your ``~/radis.json``
          :ref:`configuration file <label_lbl_config_file>`.
          This allows to use multiple database files.

        Default ``'hitran'``. See :class:`~radis.lbl.loader.DatabankLoader` for more
        information on line databases, and :data:`~radis.misc.config.DBFORMAT` for
        your ``~/radis.json`` file format.

        For multiple molecules, use a dictionary with molecule names as keys::

            databank='hitran'     # automatic download (or 'hitemp')
            databank='PATH/TO/05_HITEMP2019.par'    # path to a file
            databank='*CO2*.par' #to get all the files that have CO2 in their names (case insensitive)
            databank='HITEMP-2019-CO'   # user-defined database in Configuration file
            databank = {'CO2' : 'PATH/TO/05_HITEMP2019.par', 'CO' : 'hitran'}  # for multiple molecules

    Other Parameters
    ----------------
    medium: ``'air'``, ``'vacuum'``
        propagating medium when giving inputs with ``'wavenum_min'``, ``'wavenum_max'``.
        Does not change anything when giving inputs in wavenumber. Default ``'air'``​ .
    wstep: float (:math:`cm^{-1}`)  or `'auto'`
        Resolution of wavenumber grid. Default ``0.01`` cm-1.
        If `'auto'`, it is ensured that there
        are slightly more or less than :py:data:`~radis.params.GRIDPOINTS_PER_LINEWIDTH_WARN_THRESHOLD`
        points for each linewidth.

        .. note::
            wstep = 'auto' is optimized for performances while ensuring accuracy,
            but is still experimental in 0.9.30. Feedback welcome!
    broadening_max_width: float (cm-1)
        Full width over which to compute the broadening. Large values will create
        a huge performance drop (scales as :math:`~{w_{width}}^2` without LDM)
        The calculated spectral range is increased (by broadening_max_width/2
        on each side) to take into account overlaps from out-of-range lines.
        Default ``10`` cm-1.​
    cutoff: float (~ unit of Linestrength: :math:`cm^{-1}/(molec.cm^{-2})`)
        discard linestrengths that are lower that this, to reduce calculation
        times. ``1e-27`` is what is generally used to generate line databases such as
        CDSD. If ``0``, no cutoff. Default ``1e-27``..
    parsum_mode: 'full summation', 'tabulation'
        how to compute partition functions, at nonequilibrium or when partition
        function are not already tabulated. ``'full summation'`` : sums over all
        (potentially millions) of rovibrational levels. ``'tabulation'`` :
        builds an on-the-fly tabulation of rovibrational levels (500 - 4000x faster
        and usually accurate within 0.1%). Default ``full summation'``

        .. note::
            parsum_mode= 'tabulation'  is new in 0.9.30, and makes nonequilibrium
            calculations of small spectra extremelly fast. Will become the default
            after 0.9.31.
    optimization : ``"simple"``, ``"min-RMS"``, ``None``
        If either ``"simple"`` or ``"min-RMS"`` LDM optimization for lineshape calculation is used:

        - ``"min-RMS"`` : weights optimized by analytical minimization of the RMS-error (See: [Spectral-Synthesis-Algorithm]_)
        - ``"simple"`` : weights equal to their relative position in the grid

        If using the LDM optimization, broadening method is automatically set to ``'fft'``.
        If ``None``, no lineshape interpolation is performed and the lineshape of all lines is calculated.
        Refer to [Spectral-Synthesis-Algorithm]_ for more explanation on the LDM method for lineshape interpolation.
        Default ``"min-RMS"``.
    overpopulation: dict
        dictionary of overpopulation compared to the given vibrational temperature.
        Default ``None``. Example::

            overpopulation = {'CO2' : {'(00`0`0)->(00`0`1)': 2.5,
                                       '(00`0`1)->(00`0`2)': 1,
                                       '(01`1`0)->(01`1`1)': 1,
                                       '(01`1`1)->(01`1`2)': 1 }
                             }​
    export_lines: boolean
        if ``True``, saves details of all calculated lines in Spectrum. This is
        necessary to later use :py:meth:`~radis.spectrum.spectrum.Spectrum.line_survey`,
        but can take some space. Default ``False``.
    name: str
        name of the output Spectrum. If ``None``, a unique ID is generated.
    save_to: str
        save to a `.spec` file which contains absorption & emission features, all
        calculation parameters, and can be opened with :py:func:`~radis.tools.database.load_spec`.
        File can be reloaded and exported to text formats afterwards, see
        :py:meth:`~radis.spectrum.spectrum.Spectrum.savetxt`.
        If file already exists, replace.
    use_cached: boolean
        use cached files for line database and energy database. Default ``True``.​
    verbose: boolean, or int
        If ``False``, stays quiet. If ``True``, tells what is going on.
        If ``>=2``, gives more detailed messages (for instance, details of
        calculation times). Default ``True``.​
    mode: ``'cpu'``, ``'gpu'``
        if set to ``'cpu'``, computes the spectra purely on the CPU. if set to ``'gpu'``,
        offloads the calculations of lineshape and broadening steps to the GPU
        making use of parallel computations to speed up the process. Default ``'cpu'``.
        Note that ``mode='gpu'`` requires CUDA compatible hardware to execute.
        For more information on how to setup your system to run GPU-accelerated
        methods using CUDA and Cython, check `GPU Spectrum Calculation on RADIS <https://radis.readthedocs.io/en/latest/lbl/gpu.html>`__
    **kwargs: other inputs forwarded to SpectrumFactory
        For instance: ``warnings``.
        See :class:`~radis.lbl.factory.SpectrumFactory` documentation for more
        details on input.

    Returns
    -------
    :class:`~radis.spectrum.spectrum.Spectrum`
        Output spectrum:

        - Use the :py:meth:`~radis.spectrum.spectrum.Spectrum.get` method to retrieve a
          spectral quantity (``'radiance'``, ``'radiance_noslit'``, ``'absorbance'``, etc...)
        - Or the :py:meth:`~radis.spectrum.spectrum.Spectrum.plot` method to plot it
          directly.
        - See [1]_ to get an overview of all Spectrum methods

    References
    ----------
    .. [1] RADIS doc: `Spectrum how to? <https://radis.readthedocs.io/en/latest/spectrum/spectrum.html#label-spectrum>`__

    ​.. [2] RADIS GPU support: `GPU Calculations on RADIS <https://radis.readthedocs.io/en/latest/lbl/gpu.html>`__
    ​
    Examples
    --------
    Calculate a CO spectrum from the HITRAN database::

        from radis import calc_spectrum
        s = calc_spectrum(1900, 2300,         # cm-1
                          molecule='CO',
                          isotope='1,2,3',
                          pressure=1.01325,   # bar
                          Tgas=1000,
                          mole_fraction=0.1,
                          databank='hitran',  # or 'hitemp'
                          )
        s.apply_slit(0.5, 'nm')
        s.plot('radiance')

    This example uses the :py:meth:`~radis.spectrum.spectrum.Spectrum.apply_slit`
    and :py:meth:`~radis.spectrum.spectrum.Spectrum.plot` methods. See also
    :py:meth:`~radis.spectrum.spectrum.Spectrum.line_survey`::

        s.line_survey(overlay='radiance')

    Calculate a CO2 spectrum from the CDSD-4000 database::

        s = calc_spectrum(2200, 2400,   # cm-1
                          molecule='CO2',
                          isotope='1',
                          databank='/path/to/cdsd/databank/in/npy/format/',
                          pressure=0.1,  # bar
                          Tgas=1000,
                          mole_fraction=0.1,
                          mode='gpu'
                          )

        s.plot('absorbance')

    This example uses the :py:meth:`~radis.lbl.factory.SpectrumFactory.eq_spectrum_gpu` method to calculate
    the spectrum on the GPU. The databank points to the CDSD-4000 databank that has been
    pre-processed and stored in ``numpy.npy`` format.
    ​
    Refer to the online :ref:`Examples <label_examples>` for more cases, and to
    the :ref:`Spectrum page <label_spectrum>` for details on post-processing methods.

    For more details on how to use the GPU method and process the database, refer to the examples
    linked above and the documentation on :ref:`GPU support for RADIS <label_radis_gpu>`.
    ​
    .. minigallery:: radis.lbl.calc.calc_spectrum
        :add-heading:

    References
    ----------
    **cite**: RADIS is built on the shoulders of many state-of-the-art packages and databases. If using RADIS
    to compute spectra, make sure you cite all of them, for proper reproducibility and acknowledgement of
    the work ! See :ref:`How to cite? <label_cite>`

    See Also
    --------
    :py:class:`~radis.lbl.factory.SpectrumFactory`
    """
    from radis.los.slabs import MergeSlabs

    if molecule is not None and type(molecule) != list:
        molecule = [molecule]  # fall back to the other case: multiple molecules

    # Stage 1. Find all molecules, whatever the user input configuration

    # ... Input arguments that CAN be dictionaries of molecules.
    DICT_INPUT_ARGUMENTS = {
        "isotope": isotope,
        "mole_fraction": mole_fraction,
        "databank": databank,
    }
    # Same, but when the values of the arguments themselves are already a dict.
    # (dealt with separately because we cannot use them to guess what are the input molecules)
    DICT_INPUT_DICT_ARGUMENTS = {"overpopulation": overpopulation}

    def _check_molecules_are_consistent(
        molecule_reference_set, reference_name, new_argument, new_argument_name
    ):
        """Will test that molecules set are the same in molecule_reference_set
        and new_argument, if new_argument is a dict. molecule_reference_set is
        a set of molecules (yeah!). reference_name is the name of the argument
        from which we guessed the list of molecules (used to have a clear error
        message). new_argument is the new argument to check new_argument_name
        is its name.

        Returns the set of molecules as found in new_argument, if applicable, else the molecule_reference_set (this allows us to parse all arguments too)

        Note that names are just here to provide clear error messages to the user if there is a contradiction.
        """
        if isinstance(new_argument, dict):
            if molecule_reference_set is None:  # input molecules are still unknown
                return set(new_argument.keys()), new_argument_name
            elif set(new_argument.keys()) != set(molecule_reference_set):
                raise ValueError(
                    "Keys of molecules in the {0} dictionary must be the same as given in `{1}=`, i.e: {2}. Instead, we got {3}".format(
                        new_argument_name,
                        reference_name,
                        molecule_reference_set,
                        set(new_argument.keys()),
                    )
                )
            else:
                return (
                    set(new_argument.keys()),
                    new_argument_name,
                )  # so now we changed the reference
        else:
            return molecule_reference_set, reference_name

    # Parse all inputs:
    molecule_reference_set = molecule
    reference_name = "molecule"
    for argument_name, argument in DICT_INPUT_ARGUMENTS.items():
        molecule_reference_set, reference_name = _check_molecules_are_consistent(
            molecule_reference_set, reference_name, argument, argument_name
        )

    # ... Now we are sure there are no contradctions. Just ensure we have molecules:
    if molecule_reference_set is None:
        raise ValueError(
            "Please enter the molecule(s) to calculate in the `molecule=` argument or as a dictionary in the following: {0}".format(
                list(DICT_INPUT_ARGUMENTS.keys())
            )
        )

    # Stage 2. Now we have the list of molecules. Let's get the input arguments for each of them.

    # ... Initialize and fill the master-dictionary
    molecule_dict = {}

    for molecule in molecule_reference_set:
        molecule_dict[molecule] = {}

        for argument_name, argument_dict in DICT_INPUT_ARGUMENTS.items():
            if isinstance(argument_dict, dict):
                # Choose the correspond value
                molecule_dict[molecule][argument_name] = argument_dict[molecule]
                # Will raise a KeyError if not defined. That's fine!
                # TODO: maybe need to catch KeyError and raise a better error message?
            else:  # argument_name is not a dictionary.
                # Let's distribute the same value to every molecule:
                molecule_dict[molecule][argument_name] = argument_dict
                # If wrong argument, it will be caught in _calc_spectrum() later.

    # ... Special case of dictionary arguments. Find out if they were given as default, or per dictionary of molecules:
    is_same_for_all_molecules = dict.fromkeys(DICT_INPUT_DICT_ARGUMENTS)
    for argument_name, argument_dict in DICT_INPUT_DICT_ARGUMENTS.items():
        if not isinstance(argument_dict, dict):
            is_same_for_all_molecules[argument_name] = True
        else:
            # Argument is a dictionary. Guess if keys are molecules, or levels.
            # Ex: overpopulation dict could be {'CO2':{'(0,0,0,1)':10}} or directly {{'(0,0,0,1)':10}}
            argument_keys = set(argument_dict.keys())
            if all_in(argument_keys, molecule_reference_set):
                is_same_for_all_molecules[argument_name] = False
            else:
                is_same_for_all_molecules[argument_name] = True
    # ... now fill them in:
    for argument_name, argument_dict in DICT_INPUT_DICT_ARGUMENTS.items():
        if is_same_for_all_molecules[argument_name]:
            for mol in molecule_reference_set:
                # copy the value for everyone
                molecule_dict[mol][argument_name] = deepcopy(
                    argument_dict
                )  # in case it gets edited.
        else:  # argument_dict keys are the molecules:
            for mol in molecule_reference_set:
                molecule_dict[mol][argument_name] = argument_dict[mol]

    # Stage 3: Now let's calculate all the spectra
    s_list = []
    for molecule, dict_arguments in molecule_dict.items():
        kwargs_molecule = deepcopy(
            kwargs
        )  # these are the default supplementary arguments. Deepcopy ensures that they remain the same for all molecules, even if modified in _calc_spectrum

        # We add all of the DICT_INPUT_ARGUMENTS values:
        kwargs_molecule.update(**dict_arguments)

        s_list.append(
            _calc_spectrum(
                wavenum_min=wavenum_min,
                wavenum_max=wavenum_max,
                wavelength_min=wavelength_min,
                wavelength_max=wavelength_max,
                Tgas=Tgas,
                Tvib=Tvib,
                Trot=Trot,
                pressure=pressure,
                # overpopulation=overpopulation,  # now in dict_arguments
                molecule=molecule,
                # isotope=isotope,                # now in dict_arguments
                # mole_fraction=mole_fraction,    # now in dict_arguments
                path_length=path_length,
                # databank=databank,              # now in dict_arguments
                medium=medium,
                wstep=wstep,
                broadening_max_width=broadening_max_width,
                cutoff=cutoff,
                parsum_mode=parsum_mode,
                optimization=optimization,
                name=name,
                use_cached=use_cached,
                verbose=verbose,
                mode=mode,
                export_lines=export_lines,
                **kwargs_molecule
            )
        )

    # Stage 4: merge all molecules and return
    s = MergeSlabs(*s_list)

    if save_to:
        s.store(path=save_to, if_exists_then="replace", verbose=verbose)

    return s


def _calc_spectrum(
    wavenum_min,
    wavenum_max,
    wavelength_min,
    wavelength_max,
    Tgas,
    Tvib,
    Trot,
    pressure,
    overpopulation,
    molecule,
    isotope,
    mole_fraction,
    path_length,
    databank,
    medium,
    wstep,
    broadening_max_width,
    cutoff,
    parsum_mode,
    optimization,
    name,
    use_cached,
    verbose,
    mode,
    export_lines,
    **kwargs
):
    """See :py:func:`~radis.lbl.calc.calc_spectrum`"""

    # Check inputs

    # ... wavelengths / wavenumbers
    if (wavelength_min is not None or wavelength_max is not None) and (
        wavenum_min is not None or wavenum_max is not None
    ):
        raise ValueError("Wavenumber and Wavelength both given... it's time to choose!")

    if not medium in ["air", "vacuum"]:
        raise NotImplementedError("Unknown propagating medium: {0}".format(medium))

    if wavenum_min is None and wavenum_max is None:
        assert wavelength_max is not None
        assert wavelength_min is not None
        if medium == "vacuum":
            wavenum_min = nm2cm(wavelength_max)
            wavenum_max = nm2cm(wavelength_min)
        else:
            wavenum_min = nm2cm(air2vacuum(wavelength_max))
            wavenum_max = nm2cm(air2vacuum(wavelength_min))
    else:
        assert wavenum_min is not None
        assert wavenum_max is not None

    # ... temperatures

    if Tgas is None and Trot is None:
        raise ValueError(
            "Choose either Tgas (equilibrium) or Tvib / Trot (non equilibrium)"
        )

    if Tvib is None and Trot is not None or Tvib is not None and Trot is None:
        raise ValueError("Choose both Tvib and Trot")

    # ... others
    if databank is None:
        raise ValueError("Give a databank name")

    if not "save_memory" in kwargs:
        # no need to save intermediary results as
        # factory is used once only
        kwargs["save_memory"] = True

    if "chunksize" in kwargs:
        raise DeprecationWarning("use optimization= instead of chunksize=")

    def _is_at_equilibrium():
        try:
            assert Tvib is None or Tvib == Tgas
            assert Trot is None or Trot == Tgas
            assert overpopulation is None
            if "self_absorption" in kwargs:
                assert kwargs["self_absorption"]  # == True
            return True
        except AssertionError:
            return False

    _equilibrium = _is_at_equilibrium()

    # which columns to keep when loading line database
    if kwargs["save_memory"] >= 2 and _equilibrium:
        drop_columns = "all"
    else:
        drop_columns = "auto"

    # Run calculations
    sf = SpectrumFactory(
        wavenum_min,
        wavenum_max,
        medium=medium,
        molecule=molecule,
        isotope=isotope,
        pressure=pressure,
        wstep=wstep,
        broadening_max_width=broadening_max_width,
        cutoff=cutoff,
        parsum_mode=parsum_mode,
        verbose=verbose,
        optimization=optimization,
        export_lines=export_lines,
        **kwargs
    )
    if databank in ["fetch", "hitran", "hitemp", "exomol",] or (
        isinstance(databank, tuple) and databank[0] == "exomol"
    ):  # mode to get databank without relying on  Line databases
        # Line database :
        if databank in ["fetch", "hitran"]:
            conditions = {
                "source": "hitran",
                "parfuncfmt": "hapi",  # use HAPI (TIPS) partition functions for equilibrium
            }
        elif databank in ["hitemp"]:
            conditions = {
                "source": "hitemp",
                "parfuncfmt": "hapi",  # use HAPI (TIPS) partition functions for equilibrium}
            }
        elif databank in ["exomol"]:
            conditions = {
                "source": "exomol",
                "parfuncfmt": "exomol",  # download & use Exo partition functions for equilibrium}
            }
        elif isinstance(databank, tuple) and databank[0] == "exomol":
            conditions = {
                "source": "exomol",
                "exomol_database": databank[1],
                "parfuncfmt": "exomol",  # download & use Exo partition functions for equilibrium}
            }
        # Partition functions :
        conditions.update(
            **{
                "levelsfmt": None,  # no need to load energies by default
                "db_use_cached": use_cached,
            }
        )
        # Rovibrational energies :
        if not _equilibrium:
            # calculate partition functions with energy levels from built-in
            # constants (not all molecules are supported!)
            conditions["levelsfmt"] = "radis"
            conditions["lvl_use_cached"] = use_cached
        conditions["load_energies"] = not _equilibrium
        # Details to identify lines
        conditions["parse_local_global_quanta"] = (not _equilibrium) or export_lines
        sf.fetch_databank(**conditions)
    elif exists(databank):
        conditions = {
            "path": databank,
            "drop_columns": drop_columns,
            "parfuncfmt": "hapi",  # use HAPI (TIPS) partition functions for equilibrium
            "levelsfmt": None,  # no need to load energies by default
            "db_use_cached": use_cached,
        }
        # Guess format
        if databank.endswith(".par"):
            if verbose:
                print("Infered {0} is a HITRAN-format file.".format(databank))
            conditions["format"] = "hitran"
            # If non-equilibrium we'll also need to load the energy levels.
            if not _equilibrium:
                # calculate partition functions with energy levels from built-in
                # constants (not all molecules are supported!)
                conditions["levelsfmt"] = "radis"
                conditions["lvl_use_cached"] = use_cached
        elif databank.endswith(".h5") or databank.endswith(".hdf5"):
            if verbose:
                print(
                    "Infered {0} is a HDF5 file with RADISDB columns format".format(
                        databank
                    )
                )
            conditions["format"] = "hdf5-radisdb"
            if not _equilibrium:
                conditions["levelsfmt"] = "radis"
        else:
            raise ValueError(
                "Couldnt infer the format of the line database file: {0}. ".format(
                    databank
                )
                + "Create a user-defined database in your ~/radis.json file "
                + "and define the format there. More information on "
                + "https://radis.readthedocs.io/en/latest/lbl/lbl.html#configuration-file"
            )
        conditions["load_energies"] = not _equilibrium
        sf.load_databank(**conditions)

    else:  # manual mode: get from user-defined line databases defined in ~/radis.json
        sf.load_databank(
            databank,
            load_energies=not _equilibrium,  # no need to load/calculate energies at eq.
            drop_columns=drop_columns,
        )

    #    # Get optimisation strategies
    #    if lineshape_optimization == 'auto':        # NotImplemented: finally we use DLM all the time as default.
    #        if len(sf.df0) > 1e5:
    #            lineshape_optimization = 'DLM'
    #        else:
    #            lineshape_optimization = None
    #        sf.params['chunksize'] = lineshape_optimization

    if overpopulation is not None or overpopulation != {}:
        sf.misc.export_rovib_fraction = True  # required to compute Partition fucntions with overpopulation being taken into account

    # Use the standard eq_spectrum / non_eq_spectrum functions
    if _equilibrium:
        if mode == "cpu":
            s = sf.eq_spectrum(
                Tgas=Tgas,
                mole_fraction=mole_fraction,
                path_length=path_length,
                name=name,
            )
        elif mode == "gpu":
            s = sf.eq_spectrum_gpu(
                Tgas=Tgas,
                mole_fraction=mole_fraction,
                pressure=pressure,
                path_length=path_length,
                name=name,
            )
        else:
            raise ValueError(mode)
    else:
        if mode != "cpu":
            raise NotImplementedError(mode)
        s = sf.non_eq_spectrum(
            Tvib=Tvib,
            Trot=Trot,
            Ttrans=Tgas,
            overpopulation=overpopulation,
            mole_fraction=mole_fraction,
            path_length=path_length,
            name=name,
        )

    return s


# --------------------------
if __name__ == "__main__":

    from radis.test.lbl.test_calc import _run_testcases

    print(_run_testcases(verbose=True))
