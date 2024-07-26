<h1 align="center">
  <img src="labelsig/resource/WindowIcon.png" width="50%"><br/>LabelSIG
</h1>


<h4 align="center">
  Electrical Signal Annotation with Python
</h4>

<div align="center">
  <a href="https://pypi.python.org/pypi/LabelSIG"><img src="https://img.shields.io/pypi/v/LabelSIG.svg"></a>
  <img src="https://img.shields.io/pypi/pyversions/LabelSIG.svg"></a>
</div>

<div align="center">
  <a href="#starter-guide"><b>Starter Guide</b></a>
  | <a href="#installation"><b>Installation</b></a>
  | <a href="#usage"><b>Usage</b></a>
  | <a href="#examples"><b>Examples</b></a>
  <!-- | <a href="https://github.com/wkentaro/labelme/discussions"><b>Community</b></a> -->
  <!-- | <a href="https://www.youtube.com/playlist?list=PLI6LvFw0iflh3o33YYnVIfOpaO0hc5Dzw"><b>Youtube FAQ</b></a> -->
</div>

<br/>

# Description
LabelSIG is an electrical signal annotation tool inspired by [Labelme](https://github.com/labelmeai/labelme). Written in Python and utilizing Qt for its graphical interface, LabelSIG is designed for semantic segmentation tasks. Additionally, the tool can directly extract information from Common Format for Transient Data Exchange (COMTRADE) records. By using LabelSIG, various segments of samples are marked with different colors to easily identify their categories.
<div align="center">
  <img src="examples/semantic_segmentation/.readme/annotation.png" width="80%">
</div>
For more information or to obtain the lastest LabelSIG, please contact us via email at gaojianhong1994@foxmail.com.

## Features

- [x] Signal annotation for comtrade file. 
- [x] Annotation for fault feeder or section for earth fault localization in distribution networks.

## Starter Guide

- **Installation guides** for only Windows platforms now 💻
- **Step-by-step tutorials**: first annotation to editing, exporting, and integrating with other programs 📕
- **A compilation of valuable resources** for further exploration 🔗.

### Anaconda
You need install [Anaconda](https://www.continuum.io/downloads), then run below:

### Windows

Install [Anaconda](https://www.continuum.io/downloads), then in an Anaconda Prompt run:

```bash
conda create --name=LabeSIG python=3
conda activate LabeSIG
pip install LabeSIG
```
