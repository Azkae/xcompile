from setuptools import setup

setup(
    name='xcompile',
    version='0.1',
    install_requires=[
        'sh',
        'click'
    ],
    entry_points='''
        [console_scripts]
        xcompile=xcompile:cli
    '''
)
