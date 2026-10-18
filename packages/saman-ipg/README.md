# archipy-saman-ipg

Saman Shaparak adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): the Saman internet payment gateway.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[saman-ipg]"
```

## Usage

```python
from archipy.adapters.internet_payment_gateways.ir.saman.adapters import SamanShaparakPaymentAdapter

adapter = SamanShaparakPaymentAdapter()
```

The adapter reads its settings from the `SAMAN_SHAPARAK` section of the global config, for example `SAMAN_SHAPARAK__<FIELD>` environment variables.

Classes in `archipy.adapters.internet_payment_gateways.ir.saman.adapters`: `SamanShaparakPaymentAdapter`, `AsyncSamanShaparakPaymentAdapter`.

See the [Saman Shaparak tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/payment_gateways/) for the full API.
