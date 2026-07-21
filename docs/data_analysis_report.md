# MIND-small Data Analysis

Generated from normalized public MIND data. Fingerprint:
`643c53b0ce5fddf5e08a8d6f8e491ddec607a3f56c335c44d872e6e74cbd4b52`.

## Scale

| Split | Requests | Candidates | Positives | Users | Mean candidates/request | Mean positives/request |
|---|---:|---:|---:|---:|---:|---:|
| Train | 156,965 | 5,843,444 | 236,344 | 50,000 | 37.23 | 1.51 |
| Dev | 73,152 | 2,740,998 | 111,383 | 50,000 | 37.47 | 1.52 |

Median history length is 19 for train and
19 for dev. Every normalized candidate is a real exposure;
no random unexposed negative is introduced.

## Content

- 65,238 unique articles;
- 18 categories and 270 subcategories;
- empty abstract ratio: 5.23%;
- headline, category, and subcategory are present for every normalized article.

| Top category | Articles |
|---|---:|
| news | 20,039 |
| sports | 19,368 |
| finance | 3,786 |
| foodanddrink | 3,123 |
| travel | 3,013 |
| lifestyle | 2,991 |
| video | 2,712 |
| weather | 2,601 |
| health | 2,207 |
| autos | 2,076 |

## Exposure and CTR

- median article CTR: 0.0000;
- 95th-percentile article CTR: 0.2143;
- top 1% of exposed articles receive 32.52% of train exposures;
- top 10% receive 90.54%.

These are empirical dataset-window statistics, not online product CTR.

## Train/dev overlap and cold start

- overlapping users: 5,943
  (11.89% of dev users);
- overlapping exposed articles: 2,886;
- dev cold-article ratio: 46.25%.

Because dev known-user coverage is low, collaborative retrieval is evaluated with a
chronological holdout inside train. Official dev is reported as a separate cold-start
content/category surface.

## Demo world versus model evidence

The serving demo contains 3 personas, 15 requests, and
174 articles. The demo world is a deterministic serving slice and is not model evidence.
