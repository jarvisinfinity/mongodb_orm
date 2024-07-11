from setuptools import setup, find_packages

setup(
    name='mongodb_orm',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'pydantic==2.8.2',
        'motor==3.5.1'
    ],
    entry_points={
        'console_scripts': []
    },
    author='Tony Stark',
    author_email='tonystark.jarvis.infinity@gmail.com',
    description='ORM for creating a structured MongoDB model with ease.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/jarvisinfinity/mongodb_orm',
    license='MIT',
)