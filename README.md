# Nowcast Test Scraper

This is a simple utility/command line tool for fetching archival HRRR output for
testing the in-development Nowcast 0.5 and 1.0 algorithms.

## Installation

Install via `pip`/`setuptools` directly via git:

    $ pip install git+git://github.com/darothen-cc/nowcast_testing_scraper.git


## Dependencies

The easiest way to provision the dependencies for this scraper is through a 
conda environment; the included **environment.yml** contains all the 
necessary dependencies, and they are also enumerated for `setuptools` to deal
 with, although conda is the easier solution here:

- Python=2.7
- click (for easy CLI integration)
- pandas (for processing to CSV)
- pynio (for reading GRBI2)
- tqdm (for console output)
- xarray (for reading and processing GRIB2)

You can install these packages in the typical way if you'd like.

### Management with Conda

To install a stand-alone conda environment for this scraper, first clone
the repository from GitHub and then execute

    $ conda env create -f environment.yml

Then, enable the environment by executing

    $ source activate nowcast_testing_scraper_env
    
### Python 3

This scraper will also work in Python>=3.3, but it will require bleeding 
edge/dev versions of *xarray* and *pynio*, which can be obtained from GitHub:

- xarray@master
- pynio@development

## Usage

```
Usage: scrape_nowcast [OPTIONS] YEAR MONTH DAY HOUR OUTPUT_DIR

  Download and extract a set of archival HRRR forecast files for building
  test case data for the nowcasting algorithm.

  This script automates the task of downloading and subsetting test case
  data for the nowcasting algorithm by pulling data directly from the
  University of Utah's HRRR archive. It includes a Python-based `wget`
  command and processes the raw model output using xarray and pandas. You
  can configure exactly what period to download data for, including the
  number of forecast hours, the exact forecast (with 1 hour granularity) and
  the latitude-longitude range to subset.

  At a minimum, you must provide the date and time of the model run you want
  to retrieve, broken down by its YEAR, MONTH, DAY, and HOUR. E.g. to grab
  the forecast from 22Z on August 23, 2017, you would execute

  $ scrape_nowcast 2017 8 23 22 ./

  You must also indicate a directory to save the data. This can be the full
  path to the directory, or relative to the current directory. In the example
  above, it would download and process the data in the local directory.

  Optionally, you can request a certain number of forecast hours or a subset
  of the latitudes and longitudes to download using the `bounds` option.
  `bounds` expects four floating point values, indicating the lower left
  corner longitude and latitude then the upper right corner longitude and
  latitude of a bounding box containing your data.

Options:
  --n_fcst_hours INTEGER  Path to save extracted data
  --bounds FLOAT...       Coordinates of lower left and upper right corner of
                          bounding box for extraction
  --help                  Show this message and exit.
  
```

As an additional example, to extract the first two forecast hours from the 
HRRR simulation run on August 23, 2016 at 3Z but just a box bounded by the 
corners (-105, 32.5), (-100, 32.5), (-100, 37.5), (-105, 27.5):

``` shell
$ scrape_nowcast 2016 8 23 3 test --bounds -105. 32.5 -100. 37.5  --n_fcst_hours 2
```

This should produce two files, `test0/hrrr_subset.20160823.t03z.f00.csv` and 
`test0/hrrr_subset.20160823.t03z.f01.csv`, each about 2MB in size.