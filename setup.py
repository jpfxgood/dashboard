from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read().strip()

setup(
    name='terminal-dashboard',
    version=version,
    url='http://github.com/jpfxgood/dashboard',
    author="James Goodwin",
    author_email="dashboard@jlgoodwin.com",
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    description='A tool for showing a customizable graphical dashboard of various data sources in a terminal',
    long_description_content_type='text/markdown',
    long_description=long_description,
    license = 'MIT',
    keywords= [
        'dashboard',
        'monitor',
        'terminal',
        'graphs',
    ],
    install_requires=[
        'psutil',
        'elasticsearch',
        'paramiko',
        'keyring',
        'pyodbc',
        'python-dateutil',
    ],
    scripts=[
        'scripts/dashboard',
    ],
    packages=[
        'char_draw',
        'dashboard',
        'data_sources',
    ],
    python_requires='>=3.6',
)
