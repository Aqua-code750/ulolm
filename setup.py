from setuptools import setup, find_packages

setup(
    name="ulolm",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "rich>=13.0.0"
    ],
    entry_points={
        "console_scripts": [
            "ulolm=ulolm.cli:main",
        ],
    },
)
