from setuptools import setup, find_packages

setup(
    name="storage-adapter",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "google-cloud-storage",
        "opencv-python",
        "numpy",
        "pandas"
    ],
)