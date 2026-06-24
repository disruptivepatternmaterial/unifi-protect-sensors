# Entity Reference

## USL-Environmental

| Entity key | Platform | Device class | Unit | State class | Category |
|---|---|---|---|---|---|
| temperature | sensor | TEMPERATURE | C | MEASUREMENT | |
| humidity | sensor | HUMIDITY | % | MEASUREMENT | |
| illuminance | sensor | ILLUMINANCE | lx | MEASUREMENT | |
| battery | sensor | BATTERY | % | MEASUREMENT | |
| leak | binary_sensor | MOISTURE | | | |
| battery_low | binary_sensor | BATTERY | | | diagnostic |
| connectivity | binary_sensor | CONNECTIVITY | | | diagnostic |
| tamper | binary_sensor | TAMPER | | | |

## UP-AirQuality

| Entity key | Platform | Device class | Unit | State class | Category |
|---|---|---|---|---|---|
| temperature | sensor | TEMPERATURE | C | MEASUREMENT | |
| humidity | sensor | HUMIDITY | % | MEASUREMENT | |
| co2 | sensor | CO2 | ppm | MEASUREMENT | |
| pm1 | sensor | | ug/m3 | MEASUREMENT | |
| pm25 | sensor | PM25 | ug/m3 | MEASUREMENT | |
| pm4 | sensor | | ug/m3 | MEASUREMENT | |
| pm10 | sensor | PM10 | ug/m3 | MEASUREMENT | |
| voc_index | sensor | | (index 1-500) | MEASUREMENT | |
| nox_index | sensor | | (index 1-500) | MEASUREMENT | |
| aqi | sensor | AQI | | MEASUREMENT | |
| vape_index | sensor | | (index 0-100) | MEASUREMENT | |
| vape_detected | binary_sensor | | | | |
| connectivity | binary_sensor | CONNECTIVITY | | | diagnostic |

Note: Air-quality payload field names are provisional until confirmed via real device fixtures.
