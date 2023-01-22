# sqlpyd

![Github CI](https://github.com/justmars/sqlpyd/actions/workflows/main.yml/badge.svg)

Validate raw content with pydantic for consumption by sqlite-utils; utilized in the [LawSQL dataset](https://lawsql.com).

## Documentation

See [documentation](https://justmars.github.io/sqlpyd).

## Development

Checkout code, create a new virtual environment:

```sh
poetry add sqlpyd # python -m pip install sqlpyd
poetry update # install dependencies
poetry shell
```

Run tests:

```sh
pytest
```
