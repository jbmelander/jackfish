from setuptools import setup

setup(
    name='jackfish',
    version='0.0.1',
    description='DAQ and camera controller hub for systems neuroscience experiments.',
    url='https://github.com/jbmelander/jackfish',
    author='Joshua Melander and Minseung Choi',
    author_email='jbmelander@stanford.edu',
    packages=['jackfish'],
    install_requires=[
        'PyQt5',
        'pyqt5-plugins',
        'PyQt5-Qt5',
        'PyQt5-sip',
        'pyqtgraph',
        'qt5-applications',
        'qt5-tools',
        'simple-pyspin',
        'spinnaker-python',
        'numpy',
        'matplotlib',
        'labjack-ljm',
        'scikit-video'],
    include_package_data=True,
    zip_safe=False
)
