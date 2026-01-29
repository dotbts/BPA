# GATIS Sample Data
This repository contains examples on how to convert existing active transportation infrastructure data sources into the GATIS specification.

## Installation

Clone or download this repository into your desired directory.

Install [Anaconda Distribution or Miniconda](https://www.anaconda.com/download).

From the root of the repository directory that contains `environment.yml`, use Anaconda Prompt / Anaconda Client command line interface to create a new environment called `gatis-sample-data`:

```
conda env create -f environment.yml
```

Activate the environment:

```
conda activate gatis-sample-data
```

Install the gatis_sample_data module. Change directory to `src` and run:

```
pip install -e .
```

This repository is a mix of Python scripts that are run on the command line and Juypter Notebooks.

## Running

There are two folders of interest. The first, `austin` contains code for converting data from the City of Austin into GATIS format. The second `osm` contains code for downloading and converting OpenStreetMap data into GATIS (and adding in synthetic attributes for demonstration).

### Austin
Open and run through the `austin/Austin_GATIS_Conversion.ipynb` file.

### OpenStreetMap
Open and run through the `osm/OSM_GATIS_Conversion.ipynb` file.