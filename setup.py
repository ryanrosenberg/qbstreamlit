"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name="qbstreamlit", 
    version="0.0.1",
    description="Functions for quizbowl detailed stats",  
    url="https://github.com/ryanrosenberg/demo-detailed-stats",  
    author="Ryan Rosenberg", 
    author_email="ryanr345@gmail.com",  
    packages=['qbstreamlit'], 
    python_requires=">=3.7, <4",
    install_requires=[
        "pandas", 
        "numpy",
        "altair",
        "streamlit",
        "streamlit_aggrid"
        ]
)
