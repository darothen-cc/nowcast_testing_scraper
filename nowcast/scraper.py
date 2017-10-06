from __future__ import print_function

import os
import requests
from collections import namedtuple

import click
import pandas as pd
import xarray as xr
from tqdm import tqdm


Forecast = namedtuple('forecast', ['year', 'month', 'day', 'hour', 'fcst_hour'])

#: Base pattern for accessing an archival HRRR output from Utah server, using
#: Forecast objects
UTAH_CHPC_PATTERN = (
    "https://pando-rgw01.chpc.utah.edu/HRRR/oper/sfc/"
    "2017{fcst.month:02d}{fcst.day:02d}/"
    "hrrr.t{fcst.hour:02d}z.wrfsfcf{fcst.fcst_hour:02d}.grib2"
)

#: Base pattern for output files, using Forecast objects
FN_PATTERN = (
    "hrrr.{fcst.year:4d}{fcst.month:02d}{fcst.day:02d}."
    "t{fcst.hour:02d}z.f{fcst.fcst_hour:02d}.grib2"
)

#: Mapping of GRIB2 field names to local references.
FIELDS_MAP = [
    ('USTM_P0_2L103_GLC0', 'u_stm'),      # Eastward winds, storm-relative (m/s)
    ('VSTM_P0_2L103_GLC0', 'v_stm'),      # Northward winds, storm-relative (# m/s)
    ('CAPE_P0_L1_GLC0', 'cape'),          # CAPE, J/kg
    ('PRATE_P0_L1_GLC0', 'precip_rate'),  # Precipitation rate, mm/hr
    ('REFD_P0_L103_GLC0', 'refl'),        # Base reflectivity, dBz
    ('gridlat_0', 'lat'),                 # Grid latitudes (2D)
    ('gridlon_0', 'lon')                  # Grid longitudes (2D)
]
OLD_FIELDS, NEW_FIELDS = map(list, zip(*FIELDS_MAP))


def wget(url, filename=None, chunk_size=1024):
    """Crude Python approximation of crude the shell command `wget`

    Parameters
    ----------
    url : str
        Full URL to the resource to download.
    filename : str (optional)
        The name of the output filename. If not supplied, will infer from the
        resource URL.
    chunk_size : int
        Byte-size of chunks to download via requests.


    Returns
    -------
    filename : str
        The name of the output filename.

    """

    if filename is None:
        filename = url.split("/")[-1]

    print("Downloading {} to {}".format(url, filename))

    r = requests.get(url, stream=True)
    headers = r.headers

    print(headers['Date'], r)
    length = int(headers['Content-Length'])
    length_mb = length * (2**-20)
    print("Length: {:d} ({:g}M) [{:s}]"
          .format(length, length_mb, headers['Content-type']))

    with open(filename, 'wb') as f:
        # The following is just a progress bar which keeps track of how many
        # bytes we've downloaded from the requested resource versus how many
        # are left.
        with tqdm(total=length, unit='B', unit_scale=True,
                  unit_divisor=chunk_size) as pb:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pb.update(chunk_size)

    return filename



def _process_ds_to_df(ds, fcst, bounds=[]):
    """ Convert a HRRR forecast file into a subset and parse for output
    as a CSV listing each grid point in the forecast.

    Parameters
    ----------
    ds : xr.Dataset
        A Dataset containing (at least) the fields processed in this
        analysis: u/v storm-relative winds, cape, reflectivity, precipitation
        rate, latitude, and longitude
    fcst : Forecast
        A Forecast object indicating the model simulation and forecast hour
        that `ds` corresponds to
    bounds : list of tuples
        The coordinates defining the lower-left and upper-right coordinates of
        a bounding box used to subset the data. Expects data in the format:
        [lower left longitude, lower left latitude,
         upper right longitude, upper right latitude]. Longitudes are expected
        to be in the range (-180, 180)

    Returns
    -------
    df : pd.DataFrame
        A DataFrame with the processed fields cleaned up and subsetted

    """

    TIMESTAMP = "{fcst.year:4d}-{fcst.month:02d}-{fcst.day:02d} " \
                "{hour:02d}:00:00"
    hour = fcst.hour + fcst.fcst_hour
    ts = TIMESTAMP.format(fcst=fcst, hour=hour)

    # Fix timestamp and field names
    ds = (
        ds.rename({old: new for old, new in FIELDS_MAP})
          .assign(time=[pd.Timestamp(ts), ])
          .set_coords('time')
    )

    # Select lat-lon subset
    if bounds:
        assert len(bounds) == 4
        ll_lon, ll_lat, ur_lon, ur_lat = bounds
        ds = ds.where((ll_lat < ds.lat) & (ds.lat < ur_lat) &
                      (ll_lon < ds.lon) & (ds.lon < ur_lon), drop=True)

    # Squeeze vertical dimensions for true 2D data
    ds = ds.sel(lv_HTGL8=1000.).squeeze()

    # Convert to DataFrame
    df = (
        ds.to_dataframe()
          .dropna()
          .reset_index(drop=True)
          [NEW_FIELDS]
    )

    return df


@click.command()
@click.argument('year', type=int)#, help="Model run year")
@click.argument('month', type=int)#, help="Model run month")
@click.argument('day', type=int)#, help="Model run day")
@click.argument('hour', type=int)#, help="Model run hour")
@click.argument('output_dir')#, help="Path to save extracted data")
@click.option('--n_fcst_hours', default=3, type=int,
              help="Path to save extracted data")
@click.option('--bounds', nargs=4, type=float,
              help="Coordinates of lower left and upper right corner"
                   " of bounding box for extraction")
def main(year, month, day, hour, bounds=None, output_dir="test_case",
         n_fcst_hours=3):
    """Download and extract a set of archival HRRR forecast files for
    building test case data for the nowcasting algorithm.

    This script automates the task of downloading and subsetting test case
    data for the nowcasting algorithm by pulling data directly from the
    University of Utah's HRRR archive. It includes a Python-based `wget`
    command and processes the raw model output using xarray and pandas. You
    can configure exactly what period to download data for, including the
    number of forecast hours, the exact forecast (with 1 hour granularity)
    and the latitude-longitude range to subset.

    At a minimum, you must provide the date and time of the model run you want
    to retrieve, broken down by its YEAR, MONTH, DAY, and HOUR. E.g. to grab
    the forecast from 22Z on August 23, 2017, you would execute

    $ scrape_nowcast 2017 8 23 22 ./

    You must also indicate a directory to save the data. This can be the full
    path to the directory, or relative to the current directory. In the example
   above, it would download and process the data in the local directory.

    Optionally, you can request a certain number of forecast hours or a
    subset of the latitudes and longitudes to download using the `bounds`
    option. `bounds` expects four floating point values, indicating the lower
    left corner longitude and latitude then the upper right corner longitude
    and latitude of a bounding box containing your data.


    """

    ts = pd.Timestamp(year, month, day, hour)
    print("Retrieving HRRR simulation from {}".format(ts.strftime("%B %-d, %Y %-HZ")))
    print("    # of forecast hours: {:d}".format(n_fcst_hours))
    if bounds:
        print("    Bounding box - lower left: ({}, {})".format(*bounds[:2]))
        print("                  upper right: ({}, {})".format(*bounds[2:]))
    print("    Archiving to {}".format(output_dir))
    print()

    forecasts = [Forecast(year, month, day, hour, fcst_hour)
                 for fcst_hour in range(n_fcst_hours)]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate over all seven forecast hours
    for f in forecasts:
        url = UTAH_CHPC_PATTERN.format(fcst=f)
        filename = FN_PATTERN.format(fcst=f)
        full_filename = os.path.join(output_dir, filename)

        # Download the forecast grib file
        _ = wget(url, full_filename)

        # Process dataset
        ds = xr.open_dataset(full_filename, engine='pynio')[OLD_FIELDS]
        df = _process_ds_to_df(ds, f, bounds)

        # Save to disk
        out_fn = full_filename.replace("grib2", "csv")
        # Tweak output name to indicate we've taken a subset of the data
        if bounds:
            out_fn = out_fn.replace("hrrr", "hrrr_subset")

        print("Writing to {}... ".format(out_fn), end="")
        df.to_csv(out_fn, index=False)

        print("done!\n")

