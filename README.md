# Bay Area Campsite Monitor

This repo has two parts:

1. A short guide to car-camping campgrounds within about 2 hours of San Francisco.
2. A Python monitor with no dependencies. It polls **Recreation.gov** (federal sites) and **ReserveCalifornia** (state parks) and alerts you when a site matching your dates opens up. Most openings at popular Bay Area campgrounds are cancellations, so polling every few minutes works much better than checking by hand.

---

## Part 1: Where to car camp near SF

Drive times are rough estimates from downtown SF with no traffic. Every campground below can be reserved and monitored by this tool.

### Marin & Sonoma
| Campground | Drive | System | Why go |
|---|---|---|---|
| **Kirby Cove** (Golden Gate NRA) | 25 min | Recreation.gov | 5 sites on a beach under the Golden Gate Bridge. Seasonal and very hard to book. |
| **China Camp SP** | 35 min | ReserveCalifornia | Walk-in sites a short carry from the lot, with bay views and mountain biking. |
| **Steep Ravine** (Mt. Tamalpais SP) | 45 min | ReserveCalifornia | Rustic cabins and sites on a bluff over the Pacific. The hardest booking in the Bay Area. |
| **Samuel P. Taylor SP** | 1 h | ReserveCalifornia | Creekside redwood sites close to Point Reyes. |
| **Sugarloaf Ridge SP** | 1 h 15 | ReserveCalifornia | Meadow campground with an observatory, near the Kenwood wineries. |
| **Bothe-Napa Valley SP** | 1 h 30 | ReserveCalifornia | Shady sites and a seasonal pool between St. Helena and Calistoga. |
| **Sonoma Coast SP** (Bodega Dunes / Wright's Beach) | 1 h 45 | ReserveCalifornia | Wright's Beach sites sit right on the sand. |
| **Liberty Glen** (Lake Sonoma) | 1 h 45 | Recreation.gov | Roomy Army Corps sites on a ridge above the lake. |

### Peninsula & Santa Cruz
| Campground | Drive | System | Why go |
|---|---|---|---|
| **Half Moon Bay State Beach** | 45 min | ReserveCalifornia | Sites behind the dunes, walking distance to town. |
| **Butano SP** | 1 h 15 | ReserveCalifornia | Quiet redwood canyon near Pescadero. |
| **Portola Redwoods SP** | 1 h 15 | ReserveCalifornia | Deep redwoods with no cell service. |
| **Henry Cowell Redwoods SP** | 1 h 30 | ReserveCalifornia | Pine-ridge campground near Felton. |
| **New Brighton State Beach** | 1 h 30 | ReserveCalifornia | Bluff-top sites; you can walk to Capitola. |
| **Sunset State Beach** | 1 h 45 | ReserveCalifornia | Dune sites behind a long, uncrowded beach. |

### East Bay & South
| Campground | Drive | System | Why go |
|---|---|---|---|
| **Mount Diablo SP** (Juniper / Live Oak) | 1 h | ReserveCalifornia | Sunset views over the Bay. Best in spring; hot in summer. |
| **Pinnacles NP** | 2 h | Recreation.gov | Big campground with condors and talus caves. Usually the easiest to book on short notice. |

**Not covered by this monitor** because they use other booking systems: East Bay Regional Parks (Del Valle, Anthony Chabot, Sunol), Santa Clara County Parks (Mt. Madonna, Uvas Canyon, Coyote Lake), San Mateo County Parks (Memorial Park), and Sonoma County Regional Parks (Spring Lake, Doran Beach). All are good options. **Big Basin Redwoods** is still rebuilding after the 2020 fire, and its main campgrounds have not reopened, so check parks.ca.gov for current status.

### Booking tips
- **Booking windows:** Recreation.gov usually opens sites 6 months ahead. ReserveCalifornia opens them 6 months ahead at 8:00 AM Pacific, on a rolling daily basis. For a popular weekend, be logged in at 8:00 sharp on the opening day.
- **Cancellations:** People cancel all the time, especially in the last 1–2 weeks before a date. This is when the monitor pays off.
- **Weeknights:** Sun–Thu nights are dramatically easier to get than weekends.
- **Shoulder season:** Coastal camping in Sept–Oct is often the warmest and clearest of the year. Spring is ideal for Mt. Diablo, Pinnacles and Sugarloaf.

---

## Part 2: The monitor

Requires Python 3.11 or newer. There is nothing to install.

```bash
cp config.example.toml config.toml        # then edit dates and searches
python -m campsite_monitor list            # catalog keys you can use in config
python -m campsite_monitor check --all     # print every current opening
python -m campsite_monitor watch -i 300    # poll every ~5 minutes and alert on new openings
```

### Config (`config.toml`)
```toml
[notify]
ntfy_topic = "my-long-random-topic"   # phone push alerts via the free ntfy app

[defaults]
start = 2026-11-06        # earliest check-in
end = 2027-04-30          # latest check-out
nights = 2
check_in_days = ["fri"]   # weekends only; remove the line for any day

[[search]]
campground = "kirby-cove"

[[search]]
campground = "mount-diablo"
facility = "juniper"      # narrow a state park to one campground
```

Per-search options:
- `nights`, `start`, `end`, `check_in_days`: override the `[defaults]` values for one search.
- `include_sites` / `exclude_sites`: glob patterns matched against site names.
- `site_types`: substring match against the site type, e.g. `"tent"`.
- `include_group = true`: also check group campgrounds.

Any campground not in the catalog works too:
- Recreation.gov: set `provider = "recreation.gov"` and `campground_id = "<id from the URL>"`.
- ReserveCalifornia: set `provider = "reservecalifornia"` and `park = "<name>"`. To find exact ids, run `python -m campsite_monitor rc-search "big basin"`.

### Alerts
The monitor always prints to the console. It can also notify you through:
- **ntfy** (`NTFY_TOPIC`)
- **Slack/Discord webhook** (`WEBHOOK_URL`)
- **email** (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`)

You can set each channel in `[notify]` or with the environment variable shown, which keeps secrets out of the file. Each opening is announced once. If someone books it and it opens up again later, you get a new alert.

### Running it 24/7
- **Your own machine or a Raspberry Pi:** run `watch`, or schedule `check` every 5 minutes with cron.
- **GitHub Actions:** see `.github/workflows/monitor.yml`. Commit your config as `monitor.toml`, add an `NTFY_TOPIC` repository secret, and the workflow runs every 10 minutes. Note that the booking sites sometimes block cloud IP ranges, so a home machine is more reliable.

### How it works
- Recreation.gov: `GET /api/camps/availability/campground/<id>/month`, fetched once per month in your date range.
- ReserveCalifornia: `POST /rdr/search/grid` on the Tyler/UseDirect backend that reservecalifornia.com uses. Park and facility ids are resolved by name from `/rdr/fd/places` and `/rdr/fd/facilities`.

Neither API is officially documented, and either could change without notice. Please keep polling gentle; every few minutes is plenty. This tool only alerts you. You still book on the official sites through the link in each alert.

### Tests
```bash
python -m unittest -v
```
