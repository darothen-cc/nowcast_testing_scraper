from setuptools import setup

setup(
    name="nowcast_testing_scraper",
    py_modules=['nowcast/scraper', ],
    entry_points='''
        [console_scripts]
        scrape_nowcast=nowcast.scraper:main
    ''',
)