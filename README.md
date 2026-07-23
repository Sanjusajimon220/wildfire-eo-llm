# wildfire-eo-llm

Satellite journalism from open Earth-observation data: burn severity, fire progression,
and a constrained LLM narrative layer whose figures are checked against the measurements.

Part of [Ground_truth](https://groundtruth-earth.netlify.app/).

---

## Chapter 1 — Tenerife, August 2023

The Arafo-Candelaria fire burned for eight days across north-east Tenerife.

| | |
|---|---|
| Burned area | **13,470 ha** |
| Inside protected boundaries | **10,628 ha — 78.9%** |
| High severity | 1,823 ha — 13.5% |
| Active-fire detections | 1,026 across 18 satellite overpasses |
| Validation | Copernicus EMS **EMSR685**: 12,273 ha — **+9.8%** |

The difference runs in the expected direction: a spectral index picks up lightly scorched
edges that a very-high-resolution delineation excludes.

**[Read the chapter →](https://sanjusajimon220.github.io/wildfire-eo-llm/)**

---

## Method

Burn severity from **Sentinel-2** dNBR (USGS / Key & Benson thresholds) with RBR
(Parks et al. 2014) reported alongside, offset-corrected, cloud-masked with Cloud Score+.
Land cover from **ESA WorldCover v200**, protected areas from **WDPA / Natura 2000**,
fire progression from **NASA FIRMS** (VIIRS 375 m). A **Sentinel-1** VH backscatter check
was run as a smoke-independent cross-check; here it was inconclusive and is reported as such.

Four different measurements, four sensors, four resolutions. They are kept distinct:
detections are hotspots, not a perimeter; severity is spectral, not a field survey;
protected-area figures are **exposure**, not ecological damage.

## On the writing

`02_generate_article.py` drafts the article from `facts_<id>.json` alone — the model never
sees an image and computes nothing. Every number in the draft is then extracted and matched
against an allowlist derived from the measurements; untraceable figures fail the build.

```bash
python 02_generate_article.py facts_tenerife_2023.json --prompt      # print the prompt
python 02_generate_article.py facts_tenerife_2023.json --dry-run \
       --check article_tenerife_2023.md                              # verify a draft
```

This checks *numbers*, not *claims*. A traceable figure can still sit inside a wrong
sentence, which is why a human edits and publishes.

## Files

```
01_tenerife_2023.ipynb              analysis -> facts_tenerife_2023.json
groundtruth_map.py                  shared interactive-map builder
02_generate_article.py              constrained draft + numeric verification
facts_tenerife_2023.json            the measurements (single source of truth)
firms_timeline_tenerife_2023.geojson  1,026 detections with time and fire power
article_tenerife_2023.md            verified draft
index.html                          the published chapter
fire_spread_tenerife_2023.html      the interactive map (self-contained)
```

## Limitations

dNBR estimates severity, not a surveyed perimeter. A single post-fire composite is used,
so low-severity edges inflate the area. Trade-wind cloud leaves gaps — masked pixels are
shown as absent, never filled in. FIRMS points are ~375 m; the ignition point is the first
*detected* pixel, not the exact origin. Nothing here counts people, homes, or ecological loss,
because none of that was measured.

## Coming

| Fire | Status |
|---|---|
| Sierra de la Culebra, Zamora — 2022 | next |
| La Mierla, Guadalajara — 2026 | awaiting clear post-fire imagery |
| Cortes de Pallás, Valencia — 2012 | pre-Sentinel; detections only |

## Data

Copernicus / ESA · NASA FIRMS · UNEP-WCMC WDPA · Copernicus EMS. All open.
