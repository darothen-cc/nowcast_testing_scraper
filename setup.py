from setuptools import setup

setup(
    name="nowcast_testing_scraper",
    description="Quick scraping utility for grabbing archival HRRR data",
    url="https://github.com/darothen-cc/nowcast_testing_scraper",
    author="Daniel Rothenberg",
    author_email="daniel@climacell.co",
    packages=['nowcast', ],
    entry_points='''
        [console_scripts]
        scrape_nowcast=nowcast.scraper:main
    ''',
    install_requires=[
        'click', 'pandas', 'pynio', 'tqdm', 'xarray'
    ],
)