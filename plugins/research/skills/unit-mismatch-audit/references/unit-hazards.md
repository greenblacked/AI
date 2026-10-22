# Unit hazards

## Inventory table

| Quantity | Where | Direction | Unit | Frame or reference | Evidence |
| --- | --- | --- | --- | --- | --- |
| inlet pressure | `inlet.csv`, column `p` | read | kPa | gauge | instrument manual p. 12 |
| launch angle | `config.yaml: theta` | read | degrees | from horizontal | README |
| drag coefficient | `drag()` argument 3 | argument | dimensionless | frontal area | docstring |
| flow | `results.csv`, `q` | written | m^3/s | volumetric | writer function |

Rows with no evidence column filled are open questions, not assumptions.

## Conversions that go wrong

| Item | Fact | Trap |
| --- | --- | --- |
| Degrees to radians | multiply by pi / 180 | A library call such as `np.sin` takes radians; `np.deg2rad` makes it explicit |
| Celsius to Kelvin | add 273.15 | Differences are equal in both; ratios and logs are not |
| Gauge to absolute pressure | add local atmospheric pressure (about 101.325 kPa at sea level) | Barometric pressure varies with altitude and weather |
| Inch to metre | 0.0254 exactly | International inch; the US survey foot differs slightly from the international foot |
| Pound-force vs pound-mass | 1 lbf = 4.448 N; 1 lb = 0.4536 kg | Both called pounds; the Mars Climate Orbiter case |
| Litre to cubic metre | 1 L = 0.001 m^3 | Off by 1000 |
| Kilobyte | 1000 bytes (kB) vs 1024 bytes (KiB) | Capacities quoted differently by vendors and operating systems |
| Decibel | 10 log10 of a power ratio, 20 log10 of an amplitude ratio | Using 10 for amplitude halves the result |
| Percent | 5 percent is 0.05 | Rates entered as 5 where 0.05 expected |
| Natural vs decimal log | ln x = 2.303 log10 x | `log` means natural in NumPy and base 10 in some other tools; read the docs |
| Per-capita vs total | total = per-capita x population | Merging national totals with per-capita rates |
| Time | seconds vs milliseconds vs ticks | Epoch seconds vs milliseconds differ by 1000 |

## Libraries

```python
import pint

ureg = pint.UnitRegistry()
p = ureg.Quantity(30, "psi").to("kPa")  # about 206.8 kPa
t = ureg.Quantity(20, "degC")  # offset unit
t_K = t.to("kelvin")  # 293.15 K
d = ureg.Quantity(5, "degC") - ureg.Quantity(2, "degC")  # a delta, pint handles it
```

Check how the library handles offset units for multiplication: it raises on `degC * 2` by default, which is the behaviour wanted. `astropy.units` and `Unitful.jl` give the same dimension checks in their ecosystems.

## Sanity ranges to start from

| Quantity | Plausible range | Suggests |
| --- | --- | --- |
| Latitude, longitude | -90 to 90, -180 to 180 | Radians or swapped columns if outside or tiny |
| Atmospheric pressure at sea level | 95 to 105 kPa | Pa, bar or hPa if off by a power of ten |
| Human body temperature | 35 to 42 Celsius | Fahrenheit if around 98 |
| Adult height | 1.4 to 2.1 m | Centimetres if around 170 |
| Speed of sound in air at 20 Celsius | about 343 m/s | Check temperature and unit |
| Earth surface gravity | 9.78 to 9.83 m/s^2 | cm/s^2 if near 981 |

A median that is an exact power of ten away from the expected range, or 273.15 away, is a unit signal; a median off by an arbitrary factor is more likely a different quantity.
