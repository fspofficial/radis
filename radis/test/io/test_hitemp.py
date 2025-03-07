# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 13:51:40 2021

@author: erwan
"""


import pytest

from radis.io.hitemp import HITEMP_MOLECULES, HITEMPDatabaseManager, fetch_hitemp
from radis.misc.config import getDatabankList


@pytest.mark.fast
def test_relevant_files_filter():
    from radis.io.hitemp import keep_only_relevant

    files = [
        "02_00000-00500_HITEMP2010.zip",
        "02_00500-00625_HITEMP2010.zip",
        "02_00625-00750_HITEMP2010.zip",
        "02_00750-01000_HITEMP2010.zip",
        "02_01000-01500_HITEMP2010.zip",
        "02_01500-02000_HITEMP2010.zip",
        "02_02000-02125_HITEMP2010.zip",
        "02_02125-02250_HITEMP2010.zip",
        "02_02250-02500_HITEMP2010.zip",
        "02_02500-03000_HITEMP2010.zip",
        "02_03000-03250_HITEMP2010.zip",
        "02_03250-03500_HITEMP2010.zip",
        "02_03500-03750_HITEMP2010.zip",
        "02_03750-04000_HITEMP2010.zip",
        "02_04000-04500_HITEMP2010.zip",
        "02_04500-05000_HITEMP2010.zip",
        "02_05000-05500_HITEMP2010.zip",
        "02_05500-06000_HITEMP2010.zip",
        "02_06000-06500_HITEMP2010.zip",
        "02_06500-12785_HITEMP2010.zip",
    ]

    assert keep_only_relevant(files)[0] == files
    assert keep_only_relevant(files, wavenum_max=300)[0] == [
        "02_00000-00500_HITEMP2010.zip"
    ]
    assert keep_only_relevant(files, wavenum_min=7000)[0] == [
        "02_06500-12785_HITEMP2010.zip"
    ]
    assert keep_only_relevant(files, wavenum_min=600, wavenum_max=800)[0] == [
        "02_00500-00625_HITEMP2010.zip",
        "02_00625-00750_HITEMP2010.zip",
        "02_00750-01000_HITEMP2010.zip",
    ]


@pytest.mark.needs_connection
def test_fetch_hitemp_OH(verbose=True, *args, **kwargs):
    """Test proper download of HITEMP OH database.

    Good to test fetch_hitemp.
    ``13_HITEMP2020.par.bz2`` is only 900 kb so it can be run on online
    tests without burning the planet 🌳

    ⚠️ if using the default `chunksize=100000`, it uncompresses in one pass
    (only 57k lines for OH) and we cannot test that appending to the same HDF5
    works. So here we use a smaller chunksize of 20,000.
    .

    """

    df = fetch_hitemp("OH", cache="regen", chunksize=20000, verbose=3 * verbose)

    assert "HITEMP-OH" in getDatabankList()

    assert len(df) == 57019

    # Load again and make sure it works (ex: metadata properly loaded etc.):
    fetch_hitemp("OH")


@pytest.mark.needs_connection
def test_fetch_hitemp_partial_download_CO2(verbose=True, *args, **kwargs):
    """Test partial download of HITEMP CO2 database.

    Good to test fetch_hitemp.
    ``CO2-02_02500-03000_HITEMP2010.h5`` is only 20 MB so it can be run on online
    tests without burning the planet too much 🌳

    """
    from os.path import basename

    from radis.io.hitemp import keep_only_relevant

    wmin = 2700
    wmax = 3000

    # Check that we won't download all databae for a reduced range:
    # ... This is done at the HITEMPDatabaseManager level
    # ... unitest for this part:
    ldb = HITEMPDatabaseManager(name=f"HITEMP-CO2", molecule="CO2")
    local_files, _ = ldb.get_filenames()
    relevant_file, file_wmin, file_wmax = keep_only_relevant(
        local_files, wavenum_min=wmin, wavenum_max=wmax
    )

    assert len(relevant_file) == 1
    assert basename(relevant_file[0]) == "CO2-02_02500-03000_HITEMP2010.h5"
    assert file_wmin == 2500
    assert file_wmax == 3000

    # Now run the full function :

    df, local_files = fetch_hitemp(
        "CO2",
        load_wavenum_min=2700,
        load_wavenum_max=3000,
        verbose=3,
        return_local_path=True,
    )

    assert "HITEMP-CO2" in getDatabankList()

    assert len(local_files) == 1
    assert basename(local_files[0]) == "CO2-02_02500-03000_HITEMP2010.h5"


@pytest.mark.needs_connection
@pytest.mark.download_large_databases
@pytest.mark.parametrize("molecule", [mol for mol in HITEMP_MOLECULES])
def test_fetch_hitemp_all_molecules(molecule, verbose=True, *args, **kwargs):
    """Test fetch HITEMP for all molecules whose download URL is available.

    ..warning::
        this downloads gigabytes of data. It is unselected by default by Pytest
        (see radis/setup.cfg)

    The bz2 compression factor gives about 17 MB / million lines :

    - OH (57 k lines) is only 900 kb
    - CO (0.7 M lines) is only ~14 Mb
    - CH4 (114 M lines) is 435 MB

    If it fails, check the databases downloaded in ~/.radisdb



    Notes
    -----

    Performance tests of chunksize tested on CO :
        - chunksize=1000000  > 22s  , 1 iteration ~ 22s
        - chunksize=100000 > 18s,  , 1 iteration ~ 4s
        - chunksize=50000 > 19s   ,1 iteration ~ 2s
        - chunksize=1000 --> 90s  ,  1 iteration << 1s
    """

    df, local_files = fetch_hitemp(
        molecule, columns=["int", "wav"], verbose=verbose, return_local_path=True
    )

    assert f"HITEMP-{molecule}" in getDatabankList()

    ldb = HITEMPDatabaseManager(
        name=f"HITEMP-{molecule}", molecule=molecule, verbose=verbose
    )
    url, Nlines, _, _ = ldb.fetch_url_Nlines_wmin_wmax()

    assert len(df) == Nlines


@pytest.mark.needs_connection
def test_partial_loading(*args, **kwargs):
    """ Assert that using partial loading of the database works """

    wmin, wmax = 2500, 4500

    # First ensures that the database is wider than this (else test is irrelevant) :
    df = fetch_hitemp("OH")
    assert df.wav.min() < wmin
    assert df.wav.max() > wmax

    # Now fetch with partial loading
    df = fetch_hitemp("OH", load_wavenum_min=wmin, load_wavenum_max=wmax)
    assert df.wav.min() >= wmin
    assert df.wav.max() <= wmax

    # Test with isotope:
    wmin = 0
    wmax = 300
    df = fetch_hitemp("OH", load_wavenum_min=wmin, load_wavenum_max=wmax, isotope="2")
    assert df.iso.unique() == 2
    df = fetch_hitemp("OH", load_wavenum_min=wmin, load_wavenum_max=wmax, isotope="1,2")
    assert set(df.iso.unique()) == {1, 2}

    # TODO : active with vaex engine implementation
    # # multiple isotope selection not implemetned with vaex
    # with pytest.raises(NotImplementedError):
    #     fetch_hitemp(
    #         "OH",
    #         load_wavenum_min=wmin,
    #         load_wavenum_max=wmax,
    #         isotope="1,2,3",
    #         engine="vaex",
    #     )


@pytest.mark.needs_connection
def test_calc_hitemp_spectrum(*args, **kwargs):
    """
    Test direct loading of HDF5 files
    """

    from astropy import units as u

    from radis import calc_spectrum

    calc_spectrum(
        wavenum_min=2500 / u.cm,
        wavenum_max=4500 / u.cm,
        molecule="OH",
        Tgas=600,
        databank="hitemp",  # test by fetching directly
        verbose=False,
    )

    calc_spectrum(
        wavenum_min=2500 / u.cm,
        wavenum_max=4500 / u.cm,
        molecule="OH",
        Tgas=600,
        databank="HITEMP-OH",  # test by loading the downloaded database
        verbose=False,
    )

    return


@pytest.mark.needs_connection
def test_calc_hitemp_CO_noneq(verbose=True, *args, **kwargs):
    """Test proper download of HITEMP CO database.

    Good to test noneq calculations with direct-download of HITEMP.

    ``05_HITEMP2020.par.bz2`` is about 14 Mb. We still download it
    (once per machine) because it allows to compute & test noneq spectra,
    which failed with direct HITEMP download in RADIS 0.9.28.

    Approximate cost for the planet 🌳 :  ~ 14 gr CO2
    (hard to evaluate !).


    """

    from astropy import units as u

    from radis import calc_spectrum

    calc_spectrum(
        wavenum_min=2000 / u.cm,
        wavenum_max=2300 / u.cm,
        molecule="CO",
        isotope="1,2",
        Tvib=1500,
        Trot=300,
        databank="hitemp",  # test by fetching directly
    )

    # Recompute with (now) locally downloaded database [note : this failed on 0.9.28]
    calc_spectrum(
        wavenum_min=2000 / u.cm,
        wavenum_max=2300 / u.cm,
        molecule="CO",
        isotope="1,2",
        Tvib=1500,
        Trot=300,
        databank="HITEMP-CO",  # registered in ~/radis.json
    )


@pytest.mark.needs_connection
@pytest.mark.download_large_databases
def test_parse_hitemp_missing_labels_issue280(*args, **kwargs):
    """Test dtype problems resulting from missing labels

    Issue 280 https://github.com/radis/radis/issues/280"""

    df = fetch_hitemp(
        "CO2", load_wavenum_min=800, load_wavenum_max=1300, verbose=3, cache="regen"
    )
    print(df.dtypes["v3u"])  # Worked


if __name__ == "__main__":
    test_relevant_files_filter()
    test_fetch_hitemp_OH()
    test_partial_loading()
    test_calc_hitemp_CO_noneq()
    test_fetch_hitemp_partial_download_CO2()
    test_calc_hitemp_spectrum()
    test_fetch_hitemp_all_molecules("OH")
    test_fetch_hitemp_all_molecules("CO")
    test_fetch_hitemp_all_molecules("CO2", verbose=3)
    test_fetch_hitemp_all_molecules("N2O", verbose=3)
    test_fetch_hitemp_all_molecules("NO", verbose=3)
