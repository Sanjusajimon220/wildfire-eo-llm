# Satellites map 13,470 hectares burned in 2023 Tenerife fire

Satellite imagery was used to map the area affected by the Arafo-Candelaria fire in the Canary Islands, Spain, which began on 15 August 2023 and was declared contained on 11 September 2023. The analysis measured burned area, spectral burn severity, land cover and the share of the mapped area falling inside protected boundaries.

## What the satellites recorded

Thermal sensors on the VIIRS and MODIS instruments, distributed through FIRMS, logged 1,026 active-fire detections. These are individual hotspot pixels seen from orbit; they are not a fire perimeter and not a count of separate fires. The first detection was recorded at 02:23 on 16 August 2023 and the last at 03:32 on 23 August 2023, giving 8 days with active detections. The first detected pixel lies at 28.35905 °N, 16.43122 °W. The highest single fire radiative power reading was 318.6 megawatts, and the summed fire radiative power across all detections was 22,703.8 megawatts.

## What burned

The mapped burned area totalled 13,470.5 hectares. Spectral severity was split across four classes: 4,862.9 hectares low (36.1 per cent), 4,047.4 hectares moderate-low (30.0 per cent), 2,737.6 hectares moderate-high (20.3 per cent) and 1,822.6 hectares high (13.5 per cent). The mean relativised burn ratio across the mapped area was 0.2948. By land cover, 8,542.6 hectares were tree cover (63.4 per cent), 2,432.8 hectares grassland (18.1 per cent), 2,197.3 hectares shrubland (16.3 per cent), 182.2 hectares built-up (1.4 per cent), 71.5 hectares cropland (0.5 per cent) and 44.2 hectares bare or sparse ground (0.3 per cent). These severity classes are estimates derived from reflectance change, not field observations.

## How much of it was protected land

Of the mapped burned area, 10,628.0 hectares fall within protected-area boundaries, a share of 78.9 per cent. Ten designated areas intersect the mapping: El Teide, Montaña de los Frailes, Barranco de Fasnia y Güímar, Las Lagunetas, Siete Lomas, La Resbala, Campeches, Tigaiga y Ruiz, Costa de Acentejo, Rambla de Castro and Corona Forestal. This figure describes exposure — burned area that sits inside those boundaries. It is a geometric overlap and carries no assessment of ecological outcome.

## How we measured this

Severity was derived from Sentinel-2 optical imagery using the differenced normalised burn ratio (USGS/Key-Benson) and the relativised burn ratio (Parks et al. 2014), with an offset of -0.0109 applied. The pre-fire composite drew on 6 Sentinel-2 scenes from 10 July to 13 August 2023 and the post-fire composite on 5 scenes from 12 September to 5 October 2023. Sentinel-1 VH backscatter change was used as a qualitative cross-check, and VIIRS/MODIS FIRMS detections supplied the timeline and first detection point. The result was compared with the official Copernicus EMS activation EMSR685, which reports 12,273 hectares; our figure of 13,470.5 hectares differs by 9.8 per cent. The comparison is a validation check, not a correction of the official figure.

## Limitations

- The differenced normalised burn ratio estimates severity from imagery; it does not produce a field-surveyed perimeter.
- A single post-fire composite was used. Low-severity edges tend to make the mapped area larger than a very-high-resolution delineation would.
- Trade-wind cloud can leave gaps in coverage. Masked pixels are reported as absent rather than filled in with estimates.
- The Sentinel-1 cross-check offers qualitative confirmation only. It is not an independent estimate of area.
- FIRMS points are detections at roughly 375 metres resolution. The ignition point given is the first pixel detected, not the exact origin.
- The protected-area figure is exposure, meaning burned area inside the boundaries. It is not a measure of ecological damage.
