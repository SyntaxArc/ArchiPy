---
title: Payment Gateways
description: API reference for the internet payment gateway adapters including Parsian Shaparak and Saman Shaparak.
---

# Payment Gateways

The `internet_payment_gateways` adapter provides integration with Iranian Shaparak payment gateways. Supports both
Parsian (SOAP/WSDL) and Saman (REST/JSON) protocols.

## Parsian Shaparak

Parsian Shaparak adapter using the SOAP protocol with WSDL service definitions.

### Adapters

::: archipy.adapters.internet_payment_gateways.ir.parsian.adapters
options:
show_root_toc_entry: false
heading_level: 3

## Saman Shaparak

Saman Shaparak adapters using the REST/JSON protocol. Includes four variants:

- **`SamanShaparakPaymentAdapter`** — Classic SEP adapter, redirects to fixed payment URL
- **`SamanNeoPgShaparakPaymentAdapter`** — Neo-PG adapter, receives dynamic payment URL from `X-IPG-Url` response header
- **`AsyncSamanShaparakPaymentAdapter`** — Async version of classic SEP adapter
- **`AsyncSamanNeoPgShaparakPaymentAdapter`** — Async version of Neo-PG adapter

### Ports

Abstract port interfaces defining the Saman Shaparak adapter contract.

::: archipy.adapters.internet_payment_gateways.ir.saman.ports
options:
show_root_toc_entry: false
heading_level: 3

### Adapters

::: archipy.adapters.internet_payment_gateways.ir.saman.adapters
options:
show_root_toc_entry: false
heading_level: 3
