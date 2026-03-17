# Contributing

Contributions are welcome. This project is primarily an educational radar simulation, and improvements to physics accuracy, signal processing, or visualization are especially valued.

## Getting Started

1. Fork the repo
2. Clone your fork
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Create a feature branch: `git checkout -b feature/your-feature`

## Adding a New Radar Mode

See [docs/extending.md](docs/extending.md) for a step-by-step guide.

## Code Standards

- Type hints on all function signatures
- Docstrings on all classes and public methods
- NumPy-vectorized operations preferred over Python loops
- All changes must pass existing tests: `pytest`

## Areas Where Help is Wanted

- Probabilistic detection modeling (Pd/Pfa curves)
- PRF agility implementation
- Aspect-dependent RCS models (Swerling cases)
- Frontend improvements (PPI scope, A-scope views)
- Additional scenario presets
- ECCM technique modeling
