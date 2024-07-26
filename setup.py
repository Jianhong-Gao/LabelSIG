from setuptools import find_packages, setup
import re

def get_version():
    filename = "LabelSIG/__init__.py"
    with open(filename) as f:
        match = re.search(r"""^__version__ = ['"]([^'"]*)['"]""", f.read(), re.M)
    if not match:
        raise RuntimeError("{} doesn't contain __version__".format(filename))
    version = match.groups()[0]
    return version

def get_install_requires():
    install_requires = [
        "github2pypi==1.0.0",
        "matplotlib==3.8.0",
        "numpy==1.26.1",
        "PyQt5==5.15.11",
        "PyQt5_sip==12.15.0",
        "pywin32==306",
        "QtPy==2.4.1",
        "setuptools==68.0.0",
    ]
    return install_requires

def get_long_description():
    try:
        with open("README.md") as f:
            long_description = f.read()
    except FileNotFoundError:
        long_description = ""
    try:
        import github2pypi
        return github2pypi.replace_url(
            slug="Jianhong-Gao/LabelSIG", content=long_description, branch="main"
        )
    except ImportError:
        return long_description

setup(
    name="LabelSIG",
    version=get_version(),
    packages=find_packages(),
    description="Signal Labeling with Python",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Jianhong Gao",
    author_email="gaojianhong1994@foxmail.com",
    url="https://github.com/Jianhong-Gao/LabelSIG",
    install_requires=get_install_requires(),
    license="MIT",
    keywords="Signal Labeling, Machine Learning",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    package_data={"labelsig": ["config/*", "external/*", "resource/*","ui_designs/*"]},
    include_package_data=True,
    python_requires='>=3.9',
    entry_points={
        "console_scripts": [
            "labelsig=labelsig.__main__:main",
            # 添加其他脚本入口点
        ],
    },
)
