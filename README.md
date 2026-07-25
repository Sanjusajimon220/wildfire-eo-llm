# wildfire-eo-llm

Satellite journalism from open Earth-observation data: fire progression, burn severity,
and a constrained language-model narrative layer whose every figure is checked against the
measurements.

Part of [Ground_truth](https://groundtruth-earth.netlify.app/).
Read the chapters: **[Tenerife 2023](https://groundtruth-earth.netlify.app/fire-tenerife-2023)** ·
**[La Mierla 2026](https://groundtruth-earth.netlify.app/fire-la-mierla-2026)**

---

## Two fires, one pipeline

The same code measures both. What changes between them is not the method but what the
satellites were able to see — and saying clearly what *couldn't* be measured is part of the
method, not a footnote to it.

### Chapter 1 — Tenerife, August 2023 *(complete)*

The Arafo-Candelaria fire burned for eight days across north-east Tenerife.

| | |
|---|---|
| Burned area | **13,470 ha** |
| Inside protected boundaries | **10,628 ha — 78.9 %** |
| High severity | 1,823 ha — 13.5 % |
| Active-fire detections | 1,026 across 18 satellite overpasses |
| Validation | Copernicus EMS **EMSR685**: 12,273 ha — **+9.8 %** |

A finished fire, in the archive, with an official reference to check against. The +9.8 %
runs in the expected direction: a spectral index picks up lightly scorched edges that a
very-high-resolution delineation excludes.

### Chapter 2 — La Mierla, July 2026 *(measured live, while still burning)*

Spain's largest fire of 2026, in the Sierra Norte de Guadalajara.

| | |
|---|---|
| Active-fire detections | **1,525 across 7 days** |
| Peak fire radiative power | **412.5 MW** |
| Total fire radiative power | **38,042 MW** |
| Furthest detection from origin | **37.8 km** |
| Ignition point | 1.2 km from La Mierla village, first seen 15 h after the ground report |
| Burn severity | **not yet measurable** — no clean post-fire scene |
| Sentinel-1 cross-check | **negative** at C-band, two days in — reported, not dropped |

An active fire teaches the opposite lesson to an archived one. Optical severity needs a
clear post-fire scene that does not exist yet; radar could not distinguish the scar two days
in. Both gaps are stated plainly rather than filled with a guess. When a clear Sentinel-2
scene lands and Copernicus EMS publishes its EMSR898 delineation, the same notebook produces
the severity layer and the validation, with no other change.

---

## Method

Burn severity from **Sentinel-2** dNBR (USGS / Key & Benson thresholds) with RBR
(Parks et al. 2014) alongside, offset-corrected, cloud-masked with Cloud Score+.
Land cover from **ESA WorldCover v200**, protected areas from **WDPA / Natura 2000**,
fire progression from **NASA FIRMS** (VIIRS 375 m). A **Sentinel-1** VH backscatter change
is run as a smoke-independent cross-check.

Four measurements, four sensors, four resolutions — kept distinct on purpose. Detections are
hotspots, **not** a perimeter. Severity is spectral, **not** a field survey. Protected-area
figures are **exposure**, not ecological damage. Fire radiative power is intensity at the
moment of an overpass, **not** area.

When a measurement can't be made, it isn't made. La Mierla ships with no severity figure
because no clean post-fire scene existed; the Sentinel-1 check is reported as a negative
because it came back negative. A measurement declined, with the reason stated, is worth more
than one that's fudged.

## On the writing

`02_generate_article.py` drafts each article from `facts_<id>.json` alone — the model never
sees an image and computes nothing. Every number in the draft is then extracted and matched
against an allowlist derived from the measurements; untraceable figures fail the build.

```bash
python 02_generate_article.py facts_la_mierla_2026.json --prompt      # print the prompt
python 02_generate_article.py facts_la_mierla_2026.json --dry-run \
       --check article_la_mierla_2026.md                              # verify a draft
```

This checks **numbers**, not **claims**. A traceable figure can still sit inside a wrong
sentence, which is why a human edits and publishes. The guarantee is narrow and honest: no
figure reaches publication without a traceable source.

## Reproduce it

Each chapter runs in Google Colab, authenticated to Earth Engine. Set the CONFIG cell —
dates, area of interest, official reference — run through to `facts_<id>.json`, then build
the map and the article. The map builder and article generator are shared across all fires.

```python
import groundtruth_map as gm
gm.build(CONFIG, AOI, PLACES, severity=severity, burn_mask=burn_mask)
```

For a fire with no clean post-fire scene (like La Mierla), the notebook detects it, skips
severity automatically, and still produces the detections, radar check and article.

## Files

```
01_tenerife_2023.ipynb                 Chapter 1 analysis  -> facts_tenerife_2023.json
01_la_mierla_2026.ipynb                Chapter 2 analysis  -> facts_la_mierla_2026.json
groundtruth_map.py                     shared interactive-map builder
02_generate_article.py                 constrained draft + numeric verification

facts_tenerife_2023.json               Chapter 1 measurements (single source of truth)
facts_la_mierla_2026.json              Chapter 2 measurements
firms_timeline_tenerife_2023.geojson   1,026 detections, with time and fire power
firms_timeline_la_mierla_2026.geojson  1,525 detections
article_tenerife_2023.md               verified draft
article_la_mierla_2026.md              verified draft
fire_spread_tenerife_2023.html         self-contained interactive map
fire_spread_la_mierla_2026.html        self-contained interactive map
```

The published chapters live on the [Ground_truth site](https://groundtruth-earth.netlify.app/);
the interactive maps here are the same self-contained files those pages embed.

## Coming

| Fire | Status |
|---|---|
| Sierra de la Culebra, Zamora — 2022 | next — finished fire, biosphere reserve, EMS reference |
| Cortes de Pallás, Valencia — 2012 | pre-Sentinel; detections only, where the open archive runs out |
| La Mierla severity | when a clear post-fire scene is acquired |

## Data

Sentinel-1 & Sentinel-2 — Copernicus / ESA · Active fire — NASA FIRMS (VIIRS) ·
Land cover — ESA WorldCover v200 · Protected areas — UNEP-WCMC WDPA ·
Validation — Copernicus EMS. Accessed via Google Earth Engine. All open.
