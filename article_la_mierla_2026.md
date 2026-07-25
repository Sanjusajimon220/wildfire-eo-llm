# Spain's biggest fire of 2026, measured from orbit while it burned

Between 16 and 23 July 2026 a fire in the Sierra Norte de Guadalajara grew into the largest in Spain this year. This brief reports what satellites recorded while it was still active: where it started, how far it travelled, how much energy it radiated, and what could not yet be measured.

## What the satellites recorded

The fire was reported from the ground at 13:55 local time on 16 July 2026. The first satellite detection came at 02:41 UTC on 17 July, from the VIIRS instrument distributed through NASA FIRMS. Between then and 23 July, VIIRS logged 1,525 active-fire detections across 7 days. These are hotspot pixels seen from orbit at 375-metre resolution; they are not a fire perimeter and not a count of separate fires. The first detected pixel lies at 40.94775 °N, 3.22391 °W, about 1.2 kilometres from the village of La Mierla. The furthest detection sits 37.8 kilometres from that first point.

## How much energy the fire radiated

The highest single fire radiative power reading was 412.5 megawatts, and the summed fire radiative power across all detections was 38,042.3 megawatts. Fire radiative power measures the energy a fire emits at the moment of an overpass; it is an indicator of intensity, not a measure of area or damage. Detections were spatially clustered to confirm they represent one fire rather than several: 99.6 per cent fell into a single cluster.

## What could not be measured

Burn severity is estimated by comparing satellite imagery from before and after a fire. For this fire, 45 usable Sentinel-2 scenes were available before ignition and none after it, because the area remained under smoke and cloud while the fire was active. No burned-area figure, severity breakdown, land-cover split, or protected-area share is reported here, because none has been measured. Those figures require a clear post-fire scene, which had not yet been acquired.

## The radar cross-check

Sentinel-1 radar was used as a smoke-independent check, since its C-band signal passes through smoke where optical sensors cannot. One radar scene was available after ignition, acquired on 18 July, two days into the fire, and compared against 10 matched pre-fire scenes on the same orbit. The backscatter change inside the fire footprint was 0.473 decibels, against 0.277 decibels outside it — a difference of 0.196 decibels, below the threshold set for confirmation. On that date, radar could not distinguish burned ground from unburned. This is reported as a negative result rather than omitted. Two days into a still-spreading fire, over forest, with a single scene, a clear radar signal was not expected.

## How we measured this

Fire progression, ignition point and radiative power come from NASA FIRMS (VIIRS, near-real-time product). The radar cross-check uses Sentinel-1 GRD, VH polarisation, orbit-matched. Copernicus Emergency Management Service activated rapid mapping for this fire on 19 July 2026 (EMSR898); when its delineation is published, the burned-area figure measured here will be compared against it, as was done for the 2023 Tenerife fire. Every dataset is open.

## Limitations

- Measured while the fire was still active; the figures describe the situation up to 23 July 2026.
- No clean post-fire Sentinel-2 scene existed yet, so burn severity is not reported.
- FIRMS points are roughly 375 metres in resolution. The ignition point is the first *detected* pixel, not the exact origin.
- The Sentinel-1 cross-check is a qualitative contrast, not an independent estimate of area, and here it was negative.
- Nothing here counts people, homes, or ecological loss, because none of that was measured.

---

*Drafted by a language model from measured data only (`facts_la_mierla_2026.json`), then edited and checked by a human. An automated step verifies that every figure in this text is traceable to the measurements; the draft is rejected if any figure is not.*
