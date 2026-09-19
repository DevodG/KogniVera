# PS-04 — your data model

**PackagePro — Dynamic Tour Packages**  
Kognivera Hackathon 2026 · Travel & Tourism · data model v1.1.0-rc1

> **The problem statement itself, the 24-hour MVP scope and the XR device requirement live in the hackathon application**, on your statement's page. This document is the data you have been given to build it with: every table, every field, and what each one is for.

---

You have **28,103 rows across 21 tables**. 20 of them are the tables this statement is built on; the remaining 1 is a reference table the others point at, included so the database works on its own.

All of it is in the `data/` folder beside this document: as `PS-04.db` (SQLite, indexed, ready to query), as CSV, and as DDL for Postgres and SQLite.

## What the data gives you

60 curated packages decomposed into 420 **individually swappable** components with signed price deltas, plus 120 guides with languages, specialisations and a 30-day availability calendar.

## Watch out for this one

`price_delta` is signed and can be negative. Reprice as base + the deltas you keep, in Decimal — a float here produces a total that is 0.01 off and impossible to explain.

## The tables this statement is built on

| Table | Rows | What you use it for |
|---|---|---|
| `bookings` | 1,996 | The order header — where inventory, payment and itinerary meet. Idempotency key is mandatory, not optional. |
| `cities` | 60 | The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one. |
| `countries` | 30 | ISO country reference. Every city, currency default and calling code resolves here. |
| `currencies` | 25 | carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2). |
| `hotels` | 300 | Fewer, richer properties. Depth (reviews, room types, media) matters more than catalogue size —. |
| `itineraries` | 803 | A versioned plan belonging to a trip. version is what makes PS-11's conflict handling tractable. |
| `itinerary_items` | 8,583 | The atom of the portal, and the single most-shared object across the thirteen builds. If a team implements one shared shape, this is it. |
| `languages` | 26 | Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model. |
| `package_components` | 420 | the swappable line. You cannot swap an item inside a pipe-separated string, and swapping is PS-04's core requirement. |
| `tour_packages` | 60 | Curated catalogues are small in real life. The depth lives in package_components. |
| `trips` | 600 | The container that gives dates, party, destination and budget to everything else. Seven statements produce or consume one. |
| `user_preferences` | 1,200 | Explicit preference signal. PS-04's language-preference requirement reads from here. |
| `users` | 1,200 | The traveller identity every personalisation hangs off. Segmented heavy / light / cold_start so APS-04 can prove cold start. |
| `amenities` | 60 | Replaces the pipe-separated amenity string. Filters in PS-02 join here. |
| `categories` | 70 | One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart. |
| `guide_availability` | 3,600 | Makes 'is this guide free on the 12th?' a real query rather than an assumption. |
| `hotel_media` | 1,500 | Image references with role and alt text. PS-05 uses hero/room rows as the fallback when no XR scene exists. |
| `price_history` | 5,950 | Computed price over time with the driving factors alongside — the shape APS-02's explainability requirement has to produce. |
| `tour_guides` | 120 | PS-04's added guide dimension — selectable by language, specialisation, availability and price. |
| `transfers` | 300 | Airport and intercity legs with cost, duration and carbon — the non-POI edges in an optimised day. |

## Reference tables, included so the database is valid

You will mostly join through these rather than think about them.

| Table | Rows | What it is |
|---|---|---|
| `hotel_room_types` | 1,200 | The bookable unit. APS-05's no-oversell guarantee is defended at this grain. |

## How they fit together

Open `02_DATA_MODEL_DIAGRAM.html` in a browser for the clickable version — it shows these tables and nothing else. Download it first; it will not render inside SharePoint.

Some tables point at "any bookable thing" using an `(entity_type, entity_id)` pair rather than a typed foreign key. That is deliberate: it is what lets one feature refer to a hotel, a flight, a point of interest or a package without a separate join table for each. The legal values of `entity_type` are in `data/enums.json`.

---

## Every field, table by table

Columns marked **PK** are the primary key. **FK** shows what a column points at. Enum columns list their legal values — anything else is rejected by the conformance check.

### `amenities`

*Reference & geography · 60 rows · IDs start `amn_`*

Replaces the pipe-separated amenity string. Filters in PS-02 join here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `amenity_id` | text | **PK** | amn_ prefixed. |
| `code` | text | UNIQUE · NOT NULL | snake_case machine code, e.g. free_wifi. |
| `label` | text | NOT NULL | Display label. |
| `amenity_group` | text | NOT NULL · one of `connectivity`, `wellness`, `food_beverage`, `family`, `accessibility`, `transport`, `business`, `outdoor` |  |
| `icon_hint` | text |  | Suggested icon name, purely advisory. |
| `updated_at` | timestamptz | NOT NULL |  |

### `categories`

*Reference & geography · 70 rows · IDs start `cat_`*

One two-level taxonomy shared by POI type, package theme and expense category — so the three never drift apart.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `category_id` | text | **PK** | cat_ prefixed. |
| `code` | text | UNIQUE · NOT NULL | snake_case. |
| `label` | text | NOT NULL |  |
| `parent_category_id` | text | FK → `categories.category_id` | Null for top-level; self-referencing. |
| `applies_to` | text | NOT NULL | poi | package | expense | mixed. |
| `updated_at` | timestamptz | NOT NULL |  |

### `currencies`

*Reference & geography · 25 rows · IDs start `cur_`*

carries the true minor-unit exponent so JPY/KWD display correctly even though storage is always DECIMAL(12,2).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `currency_id` | text | **PK** | cur_ prefixed. |
| `iso4217` | char(3) | UNIQUE · NOT NULL | e.g. INR. |
| `name` | text | NOT NULL |  |
| `symbol` | text | NOT NULL |  |
| `minor_unit_exponent` | smallint | NOT NULL | 0 for JPY/KRW, 2 default, 3 for KWD/BHD. |
| `display_locale` | text | NOT NULL | BCP-47 locale used for formatting. |
| `updated_at` | timestamptz | NOT NULL |  |

### `languages`

*Reference & geography · 26 rows · IDs start `lng_`*

Rule R6: BCP-47 is the only legal way to say 'language' anywhere in the model.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `language_id` | text | **PK** | lng_ prefixed. |
| `bcp47` | text | UNIQUE · NOT NULL | e.g. ta, hi, en-IN — never 'Tamil'. |
| `english_name` | text | NOT NULL |  |
| `native_name` | text | NOT NULL |  |
| `script` | text | NOT NULL | ISO-15924, e.g. Taml, Deva, Latn. |
| `rtl` | bool | NOT NULL | Right-to-left rendering flag. |
| `tts_supported` | bool | NOT NULL | Relevant to PS-13 voice output. |
| `updated_at` | timestamptz | NOT NULL |  |

### `price_history`

*Availability & pricing · 5,950 rows · IDs start `phs_`*

Computed price over time with the driving factors alongside — the shape APS-02's explainability requirement has to produce.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `history_id` | text | **PK** | phs_ prefixed. |
| `entity_type` | text | NOT NULL · one of `room_type`, `flight_fare`, `guide`, `poi` |  |
| `entity_id` | text | NOT NULL |  |
| `effective_date` | date | NOT NULL |  |
| `price` | decimal(12,2) | NOT NULL | D3. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `baseline_price` | decimal(12,2) | NOT NULL |  |
| `demand_index` | decimal(6,3) | NOT NULL | Forecast output that drove the move. |
| `occupancy_pct` | decimal(5,2) | NOT NULL |  |
| `lead_time_factor` | decimal(6,3) | NOT NULL |  |
| `seasonality_factor` | decimal(6,3) | NOT NULL |  |
| `event_factor` | decimal(6,3) | NOT NULL | Uplift from a festival in events_festivals. |
| `competitor_factor` | decimal(6,3) | NOT NULL |  |
| `bound_clamped` | bool | NOT NULL | True where price_bounds clipped the computed price. |
| `explanation` | text | NOT NULL | Human-readable factor summary. |
| `computed_at` | timestamptz | NOT NULL |  |

*Unique together:* `(entity_type, entity_id, effective_date)`

### `countries`

*Reference & geography · 30 rows · IDs start `cnt_`*

ISO country reference. Every city, currency default and calling code resolves here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `country_id` | text | **PK** | Canonical ID, cnt_ prefixed. |
| `iso2` | char(2) | UNIQUE · NOT NULL | ISO-3166-1 alpha-2, e.g. IN. |
| `iso3` | char(3) | UNIQUE · NOT NULL | ISO-3166-1 alpha-3, e.g. IND. |
| `name` | text | NOT NULL | English short name. |
| `default_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL | ISO-4217 code. |
| `calling_code` | text | NOT NULL | E.164 country calling code, e.g. +91. |
| `region` | text | NOT NULL | UN sub-region grouping. |
| `updated_at` | timestamptz | NOT NULL | Rule R4: UTC, ISO-8601 with offset. |

### `cities`

*Reference & geography · 60 rows · IDs start `cty_`*

The geographic anchor of the whole model. 60 cities; every hotel, POI, package, advisory and weather row hangs off one.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `city_id` | text | **PK** | cty_ prefixed. |
| `name` | text | NOT NULL | City name. |
| `state` | text |  | State / province, nullable for city-states. |
| `country_id` | text | FK → `countries.country_id` · NOT NULL |  |
| `country_code` | char(2) | NOT NULL | Denormalised ISO2 for convenient joins. |
| `lat` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `lng` | decimal(9,6) | NOT NULL | Rule R7: WGS-84, 6dp. |
| `timezone` | text | NOT NULL | IANA zone, e.g. Asia/Kolkata. |
| `region` | text | NOT NULL | Domestic region grouping, e.g. South India. |
| `population` | int |  | Approximate, for demand weighting. |
| `season_profile` | text | NOT NULL · one of `winter`, `summer`, `monsoon`, `post_monsoon`, `spring`, `autumn` | Dominant season at the peak travel window. |
| `peak_months` | text | NOT NULL | Comma-separated month numbers, e.g. 10,11,12. |
| `primary_language` | text | FK → `languages.bcp47` · NOT NULL | Rule R6: BCP-47 tag. |
| `description` | text |  | One-paragraph orientation blurb, used by PS-13. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `hotels`

*Supply & catalogue · 300 rows · IDs start `htl_`*

Fewer, richer properties. Depth (reviews, room types, media) matters more than catalogue size —.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `hotel_id` | text | **PK** | htl_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `name` | text | NOT NULL | ~3% near-duplicate names injected deliberately. |
| `property_type` | text | NOT NULL · one of `hotel`, `resort`, `homestay`, `hostel`, `apartment`, `boutique`, `heritage`, `guesthouse` |  |
| `star_rating` | smallint | NOT NULL | 1–5, CHECK constrained. |
| `guest_score` | decimal(2,1) |  | 0.0–10.0; null for a handful of new properties. |
| `review_count` | int | NOT NULL | Denormalised count, must agree with hotel_reviews. |
| `address_line` | text | NOT NULL |  |
| `lat` | decimal(9,6) | NOT NULL |  |
| `lng` | decimal(9,6) | NOT NULL |  |
| `distance_to_centre_km` | decimal(6,2) | NOT NULL | PS-02 filter: distance to a landmark. |
| `description` | text | NOT NULL | Plausible prose, embeddable. |
| `base_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `checkin_time` | text | NOT NULL | Local HH:MM at the property. |
| `checkout_time` | text | NOT NULL |  |
| `chain_code` | text |  | Null for independents. |
| `has_xr_scene` | bool | NOT NULL | PS-05 / APS-07 — does an immersive preview exist. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `tour_guides`

*Supply & catalogue · 120 rows · IDs start `gid_`*

PS-04's added guide dimension — selectable by language, specialisation, availability and price.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `guide_id` | text | **PK** | gid_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `display_name` | text | NOT NULL | Synthetic. |
| `languages` | text | NOT NULL | Comma-separated BCP-47 — the PS-04 filter. |
| `specialisation` | text | NOT NULL · one of `heritage`, `food`, `trekking`, `wildlife`, `photography`, `religious`, `shopping`, `accessibility` |  |
| `secondary_specialisation` | text | one of `heritage`, `food`, `trekking`, `wildlife`, `photography`, `religious`, `shopping`, `accessibility` |  |
| `years_experience` | smallint | NOT NULL |  |
| `rating` | decimal(2,1) |  | Null for new guides. |
| `review_count` | int | NOT NULL |  |
| `day_rate` | decimal(12,2) | NOT NULL | D3. |
| `half_day_rate` | decimal(12,2) | NOT NULL |  |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `certified` | bool | NOT NULL |  |
| `bio` | text | NOT NULL | Plausible prose. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `tour_packages`

*Supply & catalogue · 60 rows · IDs start `pkg_`*

Curated catalogues are small in real life. The depth lives in package_components.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `package_id` | text | **PK** | pkg_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL | Primary destination. |
| `name` | text | NOT NULL |  |
| `theme` | text | NOT NULL · one of `adventure`, `honeymoon`, `pilgrimage`, `family`, `heritage`, `wellness`, `wildlife`, `food_trail` |  |
| `tier` | text | NOT NULL · one of `standard`, `deluxe`, `premium` |  |
| `duration_days` | smallint | NOT NULL |  |
| `duration_nights` | smallint | NOT NULL |  |
| `base_price` | decimal(12,2) | NOT NULL | the figure PS-04 reprices live. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `min_group_size` | smallint | NOT NULL |  |
| `max_group_size` | smallint | NOT NULL |  |
| `difficulty` | text | NOT NULL | easy | moderate | challenging. |
| `languages_offered` | text | NOT NULL | Comma-separated BCP-47 — PS-04 filters on this. |
| `inclusions` | text | NOT NULL | Prose summary. |
| `exclusions` | text | NOT NULL |  |
| `description` | text | NOT NULL |  |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `transfers`

*Supply & catalogue · 300 rows · IDs start `trf_`*

Airport and intercity legs with cost, duration and carbon — the non-POI edges in an optimised day.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `transfer_id` | text | **PK** | trf_ prefixed. |
| `city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `from_label` | text | NOT NULL |  |
| `to_label` | text | NOT NULL |  |
| `mode` | text | NOT NULL · one of `walk`, `cycle`, `auto_rickshaw`, `cab`, `bus`, `metro`, `train`, `ferry`, `flight` |  |
| `duration_minutes` | int | NOT NULL |  |
| `distance_km` | decimal(7,3) | NOT NULL |  |
| `cost` | decimal(12,2) | NOT NULL |  |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `carbon_kg` | decimal(8,3) | NOT NULL |  |
| `capacity_pax` | smallint | NOT NULL |  |
| `accessible` | bool | NOT NULL |  |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `users`

*Identity & preference · 1,200 rows · IDs start `usr_`*

The traveller identity every personalisation hangs off. Segmented heavy / light / cold_start so APS-04 can prove cold start.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `user_id` | text | **PK** | usr_ prefixed. |
| `display_name` | text | NOT NULL | Synthetic — no real people (content policy). |
| `email` | text | UNIQUE · NOT NULL | Synthetic @example.invalid addresses only. |
| `home_city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `home_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `locale` | text | FK → `languages.bcp47` · NOT NULL | UI language, BCP-47. |
| `budget_band` | text | NOT NULL · one of `shoestring`, `value`, `mid`, `premium`, `luxury` |  |
| `travel_style` | text | NOT NULL · one of `budget`, `comfort`, `luxury`, `adventure`, `slow`, `cultural`, `wellness` |  |
| `traveller_type` | text | NOT NULL · one of `solo`, `couple`, `family`, `business`, `friends`, `senior`, `backpacker` |  |
| `segment` | text | NOT NULL · one of `heavy`, `light`, `cold_start` | heavy / light / cold_start cohorts. |
| `date_of_signup` | date | NOT NULL |  |
| `loyalty_tier` | text |  | none | silver | gold — nullable by design. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `guide_availability`

*Supply & catalogue · 3,600 rows · IDs start `gav_`*

Makes 'is this guide free on the 12th?' a real query rather than an assumption.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `availability_id` | text | **PK** | gav_ prefixed. |
| `guide_id` | text | FK → `tour_guides.guide_id` · NOT NULL |  |
| `for_date` | date | NOT NULL |  |
| `is_available` | bool | NOT NULL |  |
| `slots_available` | smallint | NOT NULL | 0, 1 or 2 half-day slots. |
| `price_multiplier` | decimal(4,2) | NOT NULL | Peak-date uplift, e.g. 1.25. |
| `updated_at` | timestamptz | NOT NULL |  |

*Unique together:* `(guide_id, for_date)`

### `hotel_room_types`

*Supply & catalogue · 1,200 rows · IDs start `rmt_` · reference table*

The bookable unit. APS-05's no-oversell guarantee is defended at this grain.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `room_type_id` | text | **PK** | rmt_ prefixed. |
| `hotel_id` | text | FK → `hotels.hotel_id` · NOT NULL |  |
| `name` | text | NOT NULL | e.g. Deluxe Garden View. |
| `max_occupancy` | smallint | NOT NULL |  |
| `max_adults` | smallint | NOT NULL |  |
| `max_children` | smallint | NOT NULL |  |
| `bed_config` | text | NOT NULL · one of `single`, `twin`, `double`, `queen`, `king`, `bunk`, `twin_double` |  |
| `size_sqm` | smallint |  |  |
| `base_rate` | decimal(12,2) | NOT NULL | NUMERIC, never FLOAT. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL | always paired with the amount. |
| `total_units` | int | NOT NULL | Deliberately scarce on some rows so APS-05 has contention. |
| `smoking_allowed` | bool | NOT NULL |  |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `package_components`

*Supply & catalogue · 420 rows · IDs start `pcm_`*

the swappable line. You cannot swap an item inside a pipe-separated string, and swapping is PS-04's core requirement.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `component_id` | text | **PK** | pcm_ prefixed. |
| `package_id` | text | FK → `tour_packages.package_id` · NOT NULL |  |
| `component_type` | text | NOT NULL · one of `hotel`, `flight`, `poi`, `transfer`, `guide`, `meal`, `insurance`, `entry_ticket` |  |
| `entity_type` | text | one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` | Polymorphic pointer — see the supply reference spine. |
| `entity_id` | text |  | Canonical ID of the referenced supply row. |
| `day_index` | smallint | NOT NULL | 1-based day within the package. |
| `slot` | text | NOT NULL | morning | afternoon | evening | overnight. |
| `title` | text | NOT NULL |  |
| `quantity` | smallint | NOT NULL |  |
| `price_delta` | decimal(12,2) | NOT NULL | signed; what swapping this line does to the total. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `is_optional` | bool | NOT NULL |  |
| `is_swappable` | bool | NOT NULL |  |
| `swap_group` | text |  | Components sharing a swap_group are alternatives for each other. |
| `updated_at` | timestamptz | NOT NULL |  |

### `trips`

*Trip & itinerary · 600 rows · IDs start `trp_`*

The container that gives dates, party, destination and budget to everything else. Seven statements produce or consume one.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `trip_id` | text | **PK** | trp_ prefixed. |
| `owner_user_id` | text | FK → `users.user_id` · NOT NULL |  |
| `title` | text | NOT NULL |  |
| `origin_city_id` | text | FK → `cities.city_id` |  |
| `destination_city_id` | text | FK → `cities.city_id` · NOT NULL |  |
| `start_date` | date | NOT NULL | Rule R4: zoneless calendar date. |
| `end_date` | date | NOT NULL |  |
| `party_size` | smallint | NOT NULL |  |
| `adults` | smallint | NOT NULL |  |
| `children` | smallint | NOT NULL |  |
| `trip_type` | text | NOT NULL · one of `solo`, `couple`, `family`, `business`, `friends`, `senior`, `backpacker` |  |
| `is_group_trip` | bool | NOT NULL | PS-11 / PS-08 filter. |
| `status` | text | NOT NULL · one of `draft`, `planning`, `confirmed`, `in_progress`, `completed`, `cancelled` |  |
| `home_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `notes` | text |  |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `user_preferences`

*Identity & preference · 1,200 rows · IDs start `prf_`*

Explicit preference signal. PS-04's language-preference requirement reads from here.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `preference_id` | text | **PK** | prf_ prefixed. |
| `user_id` | text | FK → `users.user_id` · UNIQUE · NOT NULL | One row per user. |
| `preferred_languages` | text | NOT NULL | Comma-separated BCP-47 tags, most-preferred first. |
| `guide_language` | text | FK → `languages.bcp47` | PS-04 — preferred language for guide/tour delivery. |
| `interests` | text | NOT NULL | Comma-separated category codes. |
| `dietary_flags` | text |  | vegetarian | vegan | halal | jain | none. |
| `accessibility_needs` | text |  | step_free | hearing | vision | none. |
| `preferred_currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `max_daily_budget` | decimal(12,2) |  | decimal, paired with currency below. |
| `max_daily_budget_currency` | char(3) | FK → `currencies.iso4217` |  |
| `pace` | text | NOT NULL | relaxed | balanced | packed — feeds PS-01 and APS-09. |
| `updated_at` | timestamptz | NOT NULL |  |

### `hotel_media`

*Supply & catalogue · 1,500 rows · IDs start `hmd_`*

Image references with role and alt text. PS-05 uses hero/room rows as the fallback when no XR scene exists.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `media_id` | text | **PK** | hmd_ prefixed. |
| `hotel_id` | text | FK → `hotels.hotel_id` · NOT NULL |  |
| `room_type_id` | text | FK → `hotel_room_types.room_type_id` | Null for property-level media. |
| `media_role` | text | NOT NULL · one of `hero`, `room`, `lobby`, `exterior`, `dining`, `pool`, `bathroom`, `view`, `landmark`, `menu`, `sign`, `receipt` |  |
| `file_path` | text | NOT NULL | Relative path inside the media pack. |
| `alt_text` | text | NOT NULL | Accessibility and multimodal grounding. |
| `width_px` | int | NOT NULL |  |
| `height_px` | int | NOT NULL |  |
| `sort_order` | smallint | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `itineraries`

*Trip & itinerary · 803 rows · IDs start `itn_`*

A versioned plan belonging to a trip. version is what makes PS-11's conflict handling tractable.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `itinerary_id` | text | **PK** | itn_ prefixed. |
| `trip_id` | text | FK → `trips.trip_id` · NOT NULL |  |
| `name` | text | NOT NULL |  |
| `version` | int | NOT NULL | Monotonic per itinerary. |
| `is_active` | bool | NOT NULL | Exactly one active version per trip. |
| `generated_by` | text | NOT NULL · one of `user`, `ai_planner`, `optimizer`, `agent`, `vote`, `import` | Which subsystem produced this version. |
| `total_cost` | decimal(12,2) | NOT NULL | sum of item costs, half-up at the end. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `total_duration_minutes` | int | NOT NULL |  |
| `total_carbon_kg` | decimal(10,3) | NOT NULL | APS-09 objective. |
| `optimizer_weights` | text |  | JSON string: {cost, time, carbon} weights that produced it. |
| `status` | text | NOT NULL · one of `active`, `inactive`, `archived`, `draft` |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `itinerary_items`

*Trip & itinerary · 8,583 rows · IDs start `itm_`*

The atom of the portal, and the single most-shared object across the thirteen builds. If a team implements one shared shape, this is it.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `item_id` | text | **PK** | itm_ prefixed. |
| `itinerary_id` | text | FK → `itineraries.itinerary_id` · NOT NULL |  |
| `day_index` | smallint | NOT NULL | 1-based. |
| `sort_order` | smallint | NOT NULL | Order within the day. |
| `starts_at` | timestamptz |  | Rule R4: offset-carrying; null for unscheduled items. |
| `ends_at` | timestamptz |  |  |
| `item_type` | text | NOT NULL · one of `hotel`, `flight`, `poi`, `package`, `guide`, `transfer`, `meal`, `free` |  |
| `entity_type` | text | one of `hotel`, `room_type`, `rate_plan`, `flight`, `flight_fare`, `poi`, `package`, `package_component`, `guide`, `transfer`, `event`, `xr_scene` | Polymorphic supply reference. |
| `entity_id` | text |  | Canonical ID of the referenced supply row. |
| `title` | text | NOT NULL |  |
| `cost` | decimal(12,2) | NOT NULL | D3. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `carbon_kg` | decimal(8,3) | NOT NULL |  |
| `duration_minutes` | int | NOT NULL |  |
| `source` | text | NOT NULL · one of `user`, `ai_planner`, `optimizer`, `agent`, `vote`, `import` | user | ai_planner | optimizer | agent | vote — makes a mixed plan auditable. |
| `explanation` | text |  | Where APS-04 and PS-01 surface reasoning without a parallel structure. |
| `locked` | bool | NOT NULL | APS-09 hard constraint: must-see items cannot be dropped. |
| `status` | text | NOT NULL · one of `proposed`, `confirmed`, `removed`, `replaced` | Rule R8: removed items stay visible. |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

### `bookings`

*Booking & money · 1,996 rows · IDs start `bkg_`*

The order header — where inventory, payment and itinerary meet. Idempotency key is mandatory, not optional.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `booking_id` | text | **PK** | bkg_ prefixed. |
| `user_id` | text | FK → `users.user_id` · NOT NULL |  |
| `trip_id` | text | FK → `trips.trip_id` | Null for standalone bookings. |
| `itinerary_id` | text | FK → `itineraries.itinerary_id` |  |
| `booking_reference` | text | UNIQUE · NOT NULL | Human-quotable 6-char reference. |
| `channel` | text | NOT NULL · one of `web`, `mobile_app`, `partner`, `call_centre`, `agent` |  |
| `total_amount` | decimal(12,2) | NOT NULL | must equal the sum of booking_items. |
| `currency` | char(3) | FK → `currencies.iso4217` · NOT NULL |  |
| `tax_amount` | decimal(12,2) | NOT NULL |  |
| `idempotency_key` | text | UNIQUE · NOT NULL | APS-05 — retried requests resolve to this same row. |
| `status` | text | NOT NULL · one of `pending`, `confirmed`, `partially_confirmed`, `cancelled`, `failed`, `refunded` |  |
| `confirmed_at` | timestamptz |  |  |
| `cancelled_at` | timestamptz |  |  |
| `cancellation_reason` | text |  |  |
| `created_at` | timestamptz | NOT NULL |  |
| `updated_at` | timestamptz | NOT NULL |  |

---

## The rules that apply to these fields

| # | Rule |
|---|---|
| R1 | **Additive only.** Add columns, tables and stores freely. Never rename, drop or repurpose a field that came with the data. |
| R2 | **IDs are opaque prefixed strings** — `htl_a91f3c`. Never integers, never parsed for meaning. |
| R3 | **Money is a pair**: a 2-place decimal plus an ISO-4217 currency code. Never a float. |
| R4 | **Time is ISO-8601 with an offset.** `_at` fields carry an offset; `_date` fields have no zone. |
| R5 | **Enums are lowercase snake_case** and the legal values are in `data/enums.json`. |
| R6 | **Language is a BCP-47 tag** — `ta`, not "Tamil". |
| R7 | **Geography is WGS-84** to 6 decimal places, `lat` and `lng` together or not at all. |
| R8 | **Nothing is hard-deleted.** Rows carry `status` and `updated_at`. |

Add whatever you like beside these fields — new columns, new tables, your own vector store, your own services. That is the point of R1. What you must not do is rename or re-key the fields that came with the data, because that is what would stop sixteen independent builds being put together afterwards.

`data/WORKING_WITH_THE_DATA.md` has the loading instructions, including how to read money without corrupting it. `tools/validate_conformance.py` tells you in thirty seconds whether you are still conformant.
