# archipy-parsian-ipg

Parsian Shaparak adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): the Parsian internet payment gateway.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[parsian-ipg]"
uv add "archipy[parsian-ipg-async]"
```

## Usage

```python
from archipy.adapters.internet_payment_gateways.ir.parsian.adapters import ParsianShaparakPaymentAdapter

adapter = ParsianShaparakPaymentAdapter()
```

The adapter reads its settings from the `PARSIAN_SHAPARAK` section of the global config, for example `PARSIAN_SHAPARAK__<FIELD>` environment variables.

Classes in `archipy.adapters.internet_payment_gateways.ir.parsian.adapters`: `ParsianShaparakPaymentAdapter`, `AsyncParsianShaparakPaymentAdapter`.

See the [Parsian Shaparak tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/payment_gateways/) for the full API.
