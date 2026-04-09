from setuptools import setup, find_packages

setup(
    name="ticket-analyzer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["click", "requests"],
    entry_points={
        "console_scripts": [
            "ticket-analyzer=src.cli:cli",
        ],
    },
)
