# pyeodh

[![codecov](https://codecov.io/github/EO-DataHub/pyeodh/graph/badge.svg?token=C6RZQAUJ6I)](https://codecov.io/github/EO-DataHub/pyeodh)

> [!WARNING]
> This project is in early development and should not be used in production.

A lightweight Python client for easy access to EODH APIs.

## Installation

```
pip install pyeodh
```

## Usage

See [example notebooks](notebooks/).

## Development

Install poetry - https://python-poetry.org/docs/#installation

Install package dependencies:

```
make install
```

Run QA checks and tests:

```
make check
make test
```

To recreate all VCR cassettes run:

```
make record=rewrite test
```

or only extend with new requests by using `record=new_episodes`
