# Daikin AirBase Hot Water

Home Assistant custom integration for Daikin AirBase / BRP15B61 heat pump hot water controllers.

I have submitted [a pull request](https://github.com/fredrike/pydaikin/pull/114) to the upstream [pydaikin](https://github.com/fredrike/pydaikin) library with the hope it may end up in the Home Assistant Core [Daikin integration](https://www.home-assistant.io/integrations/daikin/). In the meantime, this integration is available.

## Features

- Local polling, no cloud dependency.
- Config flow for host and optional port.
- Water heater entity for power and operation mode.
- Statistic-friendly temperature sensors for tank, target, and outside temperature.
- Boost and vacation switches.
- Boil level and vacation day number controls.
- Drive program select control.

Future energy reporting should be added as dedicated `sensor` entities once the device API has been reverse engineered. Cumulative energy sensors should use `state_class: total_increasing` and `kWh` units so Home Assistant can store long-term statistics and use them in the Energy Dashboard.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Daikin. Daikin trademarks are used only for product identification.

## HACS Installation

1. Add `https://github.com/billgeo/ha-daikin-airbase-hotwater` as a custom repository in HACS.
2. Select category `Integration`.
3. Open **Daikin AirBase Hot Water** in HACS and select **Download**.
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
