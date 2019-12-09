from setuptools import setup, find_packages

setup(
    name="fast-pssh",
    version="0.0.1",
    license="MIT Licence",
    url="deadwind",
    author_email="deadwind4@outlook.com",
    description="fast pssh",
    long_description="",
    install_requires=[
        "ssh2-python",
        "gevent",
    ],
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            'fpssh = fpssh:cli'
        ]
    },
    scripts=["fpssh_cli.py"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)

