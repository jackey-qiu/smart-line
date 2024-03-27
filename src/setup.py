import os, sys
from setuptools import setup, find_packages

install_requires=["PyQt5", "pyqtgraph", "opencv-python-headless", "lmfit", \
                  "QDarkStyle", "qimage2ndarray", "tifffile", \
                  "pytango", "taurus", "taurus-pyqtgraph", "sardana", \
                  "scikit-learn", "pandas"]
if sys.version_info.minor>7:
    install_requires = install_requires + ["trackpy", "imreg-dft"]

setup(
    name = 'smart',
    version= '0.1.0',
    description='smart multi-application running toolkit used for modern synchrotron beamline',
    author='Canrong Qiu (Jackey)',
    author_email='canrong.qiu@desy.de',
    url='https://github.com/jackey-qiu/smart-line',
    classifiers=['Topic :: x ray data analysis, beamline control',
                 'Programming Language :: Python'],
    license='MIT',
    python_requires='>=3.7, <=3.10',
    install_requires = install_requires,
    packages=find_packages(),
    package_data={'':['*.ui','*.ini','*.qrc'],'smart.bin':['*.png'], 'smart.gui.ui':['icons/*/*.png'],\
                  'smart.resource':['config/appsettings.ini']},
    entry_points = {
        'console_scripts' : [
            'smart = smart.bin.launch_app:main'
        ],
    }
)