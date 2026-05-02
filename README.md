# Daikin AirBase Hot Water

Home Assistant custom integration for Daikin AirBase / BRP15B61 heat pump hot water controllers.

This is a bridge integration while upstream `pydaikin` and Home Assistant Core support are pending. It talks directly to the local AirBase hot water API at `/skyfi/hotwater/...` over HTTP on port 80 and does not use the standard Daikin air conditioner API.

## Features

- Local polling, no cloud dependency.
- Config flow for host and optional port.
- Water heater entity for power and operation mode.
- Statistic-friendly temperature sensors for tank, target, and outside temperature.
- Boost and vacation switches.
- Boil level and vacation day number controls.
- Drive program select control.

Future energy reporting should be added as dedicated `sensor` entities once the device API has been reverse engineered. Cumulative energy sensors should use `state_class: total_increasing` and `kWh` units so Home Assistant can store long-term statistics and use them in the Energy Dashboard.

## HACS Installation

1. Add this repository as a custom repository in HACS.
2. Select category `Integration`.
3. Install **Daikin AirBase Hot Water**.
4. Restart Home Assistant.
5. Add the integration from **Settings > Devices & services**.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-test.txt
pre-commit install
pytest
ruff check .
ruff format --check .
```

