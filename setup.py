from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='aladdin_connect',
    version='0.4',
    author='Josh Shoemaker',
    author_email='shoejosh@gmail.com',
    url='http://github.com/shoejosh/aladdin-connect',
    packages=['aladdin_connect'],
    scripts=[],
    description='Python API for controlling Genie garage doors connected to Aladdin Connect devices',
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    install_requires=['requests'],
    include_package_data=True
)
