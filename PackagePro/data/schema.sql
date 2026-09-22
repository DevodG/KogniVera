-- KV Hackathon 2026 · travel data model v1.1.0-rc1
-- Only the 21 tables this problem statement needs.

CREATE EXTENSION IF NOT EXISTS vector;   -- optional, for embedding search

-- amenities  (Reference & geography)
CREATE TABLE amenities (
  amenity_id                   TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  amenity_group                TEXT NOT NULL CHECK (amenity_group IN ('connectivity', 'wellness', 'food_beverage', 'family', 'accessibility', 'transport', 'business', 'outdoor')),
  icon_hint                    TEXT,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- categories  (Reference & geography)
CREATE TABLE categories (
  category_id                  TEXT PRIMARY KEY,
  code                         TEXT NOT NULL UNIQUE,
  label                        TEXT NOT NULL,
  parent_category_id           TEXT,
  applies_to                   TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- currencies  (Reference & geography)
CREATE TABLE currencies (
  currency_id                  TEXT PRIMARY KEY,
  iso4217                      CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  symbol                       TEXT NOT NULL,
  minor_unit_exponent          SMALLINT NOT NULL,
  display_locale               TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- languages  (Reference & geography)
CREATE TABLE languages (
  language_id                  TEXT PRIMARY KEY,
  bcp47                        TEXT NOT NULL UNIQUE,
  english_name                 TEXT NOT NULL,
  native_name                  TEXT NOT NULL,
  script                       TEXT NOT NULL,
  rtl                          BOOLEAN NOT NULL,
  tts_supported                BOOLEAN NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- price_history  (Availability & pricing)
CREATE TABLE price_history (
  history_id                   TEXT PRIMARY KEY,
  entity_type                  TEXT NOT NULL CHECK (entity_type IN ('room_type', 'flight_fare', 'guide', 'poi')),
  entity_id                    TEXT NOT NULL,
  effective_date               DATE NOT NULL,
  price                        NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  baseline_price               NUMERIC(12,2) NOT NULL,
  demand_index                 NUMERIC(6,3) NOT NULL,
  occupancy_pct                NUMERIC(5,2) NOT NULL,
  lead_time_factor             NUMERIC(6,3) NOT NULL,
  seasonality_factor           NUMERIC(6,3) NOT NULL,
  event_factor                 NUMERIC(6,3) NOT NULL,
  competitor_factor            NUMERIC(6,3) NOT NULL,
  bound_clamped                BOOLEAN NOT NULL,
  explanation                  TEXT NOT NULL,
  computed_at                  TIMESTAMPTZ NOT NULL,
  UNIQUE (entity_type, entity_id, effective_date)
);

-- countries  (Reference & geography)
CREATE TABLE countries (
  country_id                   TEXT PRIMARY KEY,
  iso2                         CHAR(2) NOT NULL UNIQUE,
  iso3                         CHAR(3) NOT NULL UNIQUE,
  name                         TEXT NOT NULL,
  default_currency             CHAR(3) NOT NULL,
  calling_code                 TEXT NOT NULL,
  region                       TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- cities  (Reference & geography)
CREATE TABLE cities (
  city_id                      TEXT PRIMARY KEY,
  name                         TEXT NOT NULL,
  state                        TEXT,
  country_id                   TEXT NOT NULL,
  country_code                 CHAR(2) NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  timezone                     TEXT NOT NULL,
  region                       TEXT NOT NULL,
  population                   INTEGER,
  season_profile               TEXT NOT NULL CHECK (season_profile IN ('winter', 'summer', 'monsoon', 'post_monsoon', 'spring', 'autumn')),
  peak_months                  TEXT NOT NULL,
  primary_language             TEXT NOT NULL,
  description                  TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- hotels  (Supply & catalogue)
CREATE TABLE hotels (
  hotel_id                     TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  property_type                TEXT NOT NULL CHECK (property_type IN ('hotel', 'resort', 'homestay', 'hostel', 'apartment', 'boutique', 'heritage', 'guesthouse')),
  star_rating                  SMALLINT NOT NULL,
  guest_score                  NUMERIC(2,1),
  review_count                 INTEGER NOT NULL,
  address_line                 TEXT NOT NULL,
  lat                          NUMERIC(9,6) NOT NULL,
  lng                          NUMERIC(9,6) NOT NULL,
  distance_to_centre_km        NUMERIC(6,2) NOT NULL,
  description                  TEXT NOT NULL,
  base_currency                CHAR(3) NOT NULL,
  checkin_time                 TEXT NOT NULL,
  checkout_time                TEXT NOT NULL,
  chain_code                   TEXT,
  has_xr_scene                 BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- tour_guides  (Supply & catalogue)
CREATE TABLE tour_guides (
  guide_id                     TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  display_name                 TEXT NOT NULL,
  languages                    TEXT NOT NULL,
  specialisation               TEXT NOT NULL CHECK (specialisation IN ('heritage', 'food', 'trekking', 'wildlife', 'photography', 'religious', 'shopping', 'accessibility')),
  secondary_specialisation     TEXT CHECK (secondary_specialisation IN ('heritage', 'food', 'trekking', 'wildlife', 'photography', 'religious', 'shopping', 'accessibility')),
  years_experience             SMALLINT NOT NULL,
  rating                       NUMERIC(2,1),
  review_count                 INTEGER NOT NULL,
  day_rate                     NUMERIC(12,2) NOT NULL,
  half_day_rate                NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  certified                    BOOLEAN NOT NULL,
  bio                          TEXT NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- tour_packages  (Supply & catalogue)
CREATE TABLE tour_packages (
  package_id                   TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  theme                        TEXT NOT NULL CHECK (theme IN ('adventure', 'honeymoon', 'pilgrimage', 'family', 'heritage', 'wellness', 'wildlife', 'food_trail')),
  tier                         TEXT NOT NULL CHECK (tier IN ('standard', 'deluxe', 'premium')),
  duration_days                SMALLINT NOT NULL,
  duration_nights              SMALLINT NOT NULL,
  base_price                   NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  min_group_size               SMALLINT NOT NULL,
  max_group_size               SMALLINT NOT NULL,
  difficulty                   TEXT NOT NULL,
  languages_offered            TEXT NOT NULL,
  inclusions                   TEXT NOT NULL,
  exclusions                   TEXT NOT NULL,
  description                  TEXT NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- transfers  (Supply & catalogue)
CREATE TABLE transfers (
  transfer_id                  TEXT PRIMARY KEY,
  city_id                      TEXT NOT NULL,
  from_label                   TEXT NOT NULL,
  to_label                     TEXT NOT NULL,
  mode                         TEXT NOT NULL CHECK (mode IN ('walk', 'cycle', 'auto_rickshaw', 'cab', 'bus', 'metro', 'train', 'ferry', 'flight')),
  duration_minutes             INTEGER NOT NULL,
  distance_km                  NUMERIC(7,3) NOT NULL,
  cost                         NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  capacity_pax                 SMALLINT NOT NULL,
  accessible                   BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- users  (Identity & preference)
CREATE TABLE users (
  user_id                      TEXT PRIMARY KEY,
  display_name                 TEXT NOT NULL,
  email                        TEXT NOT NULL UNIQUE,
  home_city_id                 TEXT NOT NULL,
  home_currency                CHAR(3) NOT NULL,
  locale                       TEXT NOT NULL,
  budget_band                  TEXT NOT NULL CHECK (budget_band IN ('shoestring', 'value', 'mid', 'premium', 'luxury')),
  travel_style                 TEXT NOT NULL CHECK (travel_style IN ('budget', 'comfort', 'luxury', 'adventure', 'slow', 'cultural', 'wellness')),
  traveller_type               TEXT NOT NULL CHECK (traveller_type IN ('solo', 'couple', 'family', 'business', 'friends', 'senior', 'backpacker')),
  segment                      TEXT NOT NULL CHECK (segment IN ('heavy', 'light', 'cold_start')),
  date_of_signup               DATE NOT NULL,
  loyalty_tier                 TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- guide_availability  (Supply & catalogue)
CREATE TABLE guide_availability (
  availability_id              TEXT PRIMARY KEY,
  guide_id                     TEXT NOT NULL,
  for_date                     DATE NOT NULL,
  is_available                 BOOLEAN NOT NULL,
  slots_available              SMALLINT NOT NULL,
  price_multiplier             NUMERIC(4,2) NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL,
  UNIQUE (guide_id, for_date)
);

-- hotel_room_types  (Supply & catalogue)
CREATE TABLE hotel_room_types (
  room_type_id                 TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  name                         TEXT NOT NULL,
  max_occupancy                SMALLINT NOT NULL,
  max_adults                   SMALLINT NOT NULL,
  max_children                 SMALLINT NOT NULL,
  bed_config                   TEXT NOT NULL CHECK (bed_config IN ('single', 'twin', 'double', 'queen', 'king', 'bunk', 'twin_double')),
  size_sqm                     SMALLINT,
  base_rate                    NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  total_units                  INTEGER NOT NULL,
  smoking_allowed              BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- package_components  (Supply & catalogue)
CREATE TABLE package_components (
  component_id                 TEXT PRIMARY KEY,
  package_id                   TEXT NOT NULL,
  component_type               TEXT NOT NULL CHECK (component_type IN ('hotel', 'flight', 'poi', 'transfer', 'guide', 'meal', 'insurance', 'entry_ticket')),
  entity_type                  TEXT CHECK (entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  entity_id                    TEXT,
  day_index                    SMALLINT NOT NULL,
  slot                         TEXT NOT NULL,
  title                        TEXT NOT NULL,
  quantity                     SMALLINT NOT NULL,
  price_delta                  NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  is_optional                  BOOLEAN NOT NULL,
  is_swappable                 BOOLEAN NOT NULL,
  swap_group                   TEXT,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- trips  (Trip & itinerary)
CREATE TABLE trips (
  trip_id                      TEXT PRIMARY KEY,
  owner_user_id                TEXT NOT NULL,
  title                        TEXT NOT NULL,
  origin_city_id               TEXT,
  destination_city_id          TEXT NOT NULL,
  start_date                   DATE NOT NULL,
  end_date                     DATE NOT NULL,
  party_size                   SMALLINT NOT NULL,
  adults                       SMALLINT NOT NULL,
  children                     SMALLINT NOT NULL,
  trip_type                    TEXT NOT NULL CHECK (trip_type IN ('solo', 'couple', 'family', 'business', 'friends', 'senior', 'backpacker')),
  is_group_trip                BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('draft', 'planning', 'confirmed', 'in_progress', 'completed', 'cancelled')),
  home_currency                CHAR(3) NOT NULL,
  notes                        TEXT,
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- user_preferences  (Identity & preference)
CREATE TABLE user_preferences (
  preference_id                TEXT PRIMARY KEY,
  user_id                      TEXT NOT NULL UNIQUE,
  preferred_languages          TEXT NOT NULL,
  guide_language               TEXT,
  interests                    TEXT NOT NULL,
  dietary_flags                TEXT,
  accessibility_needs          TEXT,
  preferred_currency           CHAR(3) NOT NULL,
  max_daily_budget             NUMERIC(12,2),
  max_daily_budget_currency    CHAR(3),
  pace                         TEXT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- hotel_media  (Supply & catalogue)
CREATE TABLE hotel_media (
  media_id                     TEXT PRIMARY KEY,
  hotel_id                     TEXT NOT NULL,
  room_type_id                 TEXT,
  media_role                   TEXT NOT NULL CHECK (media_role IN ('hero', 'room', 'lobby', 'exterior', 'dining', 'pool', 'bathroom', 'view', 'landmark', 'menu', 'sign', 'receipt')),
  file_path                    TEXT NOT NULL,
  alt_text                     TEXT NOT NULL,
  width_px                     INTEGER NOT NULL,
  height_px                    INTEGER NOT NULL,
  sort_order                   SMALLINT NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- itineraries  (Trip & itinerary)
CREATE TABLE itineraries (
  itinerary_id                 TEXT PRIMARY KEY,
  trip_id                      TEXT NOT NULL,
  name                         TEXT NOT NULL,
  version                      INTEGER NOT NULL,
  is_active                    BOOLEAN NOT NULL,
  generated_by                 TEXT NOT NULL CHECK (generated_by IN ('user', 'ai_planner', 'optimizer', 'agent', 'vote', 'import')),
  total_cost                   NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  total_duration_minutes       INTEGER NOT NULL,
  total_carbon_kg              NUMERIC(10,3) NOT NULL,
  optimizer_weights            TEXT,
  status                       TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'archived', 'draft')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- itinerary_items  (Trip & itinerary)
CREATE TABLE itinerary_items (
  item_id                      TEXT PRIMARY KEY,
  itinerary_id                 TEXT NOT NULL,
  day_index                    SMALLINT NOT NULL,
  sort_order                   SMALLINT NOT NULL,
  starts_at                    TIMESTAMPTZ,
  ends_at                      TIMESTAMPTZ,
  item_type                    TEXT NOT NULL CHECK (item_type IN ('hotel', 'flight', 'poi', 'package', 'guide', 'transfer', 'meal', 'free')),
  entity_type                  TEXT CHECK (entity_type IN ('hotel', 'room_type', 'rate_plan', 'flight', 'flight_fare', 'poi', 'package', 'package_component', 'guide', 'transfer', 'event', 'xr_scene')),
  entity_id                    TEXT,
  title                        TEXT NOT NULL,
  cost                         NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  carbon_kg                    NUMERIC(8,3) NOT NULL,
  duration_minutes             INTEGER NOT NULL,
  source                       TEXT NOT NULL CHECK (source IN ('user', 'ai_planner', 'optimizer', 'agent', 'vote', 'import')),
  explanation                  TEXT,
  locked                       BOOLEAN NOT NULL,
  status                       TEXT NOT NULL CHECK (status IN ('proposed', 'confirmed', 'removed', 'replaced')),
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- bookings  (Booking & money)
CREATE TABLE bookings (
  booking_id                   TEXT PRIMARY KEY,
  user_id                      TEXT NOT NULL,
  trip_id                      TEXT,
  itinerary_id                 TEXT,
  booking_reference            TEXT NOT NULL UNIQUE,
  channel                      TEXT NOT NULL CHECK (channel IN ('web', 'mobile_app', 'partner', 'call_centre', 'agent')),
  total_amount                 NUMERIC(12,2) NOT NULL,
  currency                     CHAR(3) NOT NULL,
  tax_amount                   NUMERIC(12,2) NOT NULL,
  idempotency_key              TEXT NOT NULL UNIQUE,
  status                       TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'partially_confirmed', 'cancelled', 'failed', 'refunded')),
  confirmed_at                 TIMESTAMPTZ,
  cancelled_at                 TIMESTAMPTZ,
  cancellation_reason          TEXT,
  created_at                   TIMESTAMPTZ NOT NULL,
  updated_at                   TIMESTAMPTZ NOT NULL
);

-- foreign keys
ALTER TABLE categories ADD CONSTRAINT fk_categories_parent_category_id FOREIGN KEY (parent_category_id) REFERENCES categories(category_id);
ALTER TABLE price_history ADD CONSTRAINT fk_price_history_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE countries ADD CONSTRAINT fk_countries_default_currency FOREIGN KEY (default_currency) REFERENCES currencies(iso4217);
ALTER TABLE cities ADD CONSTRAINT fk_cities_country_id FOREIGN KEY (country_id) REFERENCES countries(country_id);
ALTER TABLE cities ADD CONSTRAINT fk_cities_primary_language FOREIGN KEY (primary_language) REFERENCES languages(bcp47);
ALTER TABLE hotels ADD CONSTRAINT fk_hotels_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE hotels ADD CONSTRAINT fk_hotels_base_currency FOREIGN KEY (base_currency) REFERENCES currencies(iso4217);
ALTER TABLE tour_guides ADD CONSTRAINT fk_tour_guides_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE tour_guides ADD CONSTRAINT fk_tour_guides_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE tour_packages ADD CONSTRAINT fk_tour_packages_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE tour_packages ADD CONSTRAINT fk_tour_packages_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE transfers ADD CONSTRAINT fk_transfers_city_id FOREIGN KEY (city_id) REFERENCES cities(city_id);
ALTER TABLE transfers ADD CONSTRAINT fk_transfers_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE users ADD CONSTRAINT fk_users_home_city_id FOREIGN KEY (home_city_id) REFERENCES cities(city_id);
ALTER TABLE users ADD CONSTRAINT fk_users_home_currency FOREIGN KEY (home_currency) REFERENCES currencies(iso4217);
ALTER TABLE users ADD CONSTRAINT fk_users_locale FOREIGN KEY (locale) REFERENCES languages(bcp47);
ALTER TABLE guide_availability ADD CONSTRAINT fk_guide_availability_guide_id FOREIGN KEY (guide_id) REFERENCES tour_guides(guide_id);
ALTER TABLE hotel_room_types ADD CONSTRAINT fk_hotel_room_types_hotel_id FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id);
ALTER TABLE hotel_room_types ADD CONSTRAINT fk_hotel_room_types_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE package_components ADD CONSTRAINT fk_package_components_package_id FOREIGN KEY (package_id) REFERENCES tour_packages(package_id);
ALTER TABLE package_components ADD CONSTRAINT fk_package_components_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE trips ADD CONSTRAINT fk_trips_owner_user_id FOREIGN KEY (owner_user_id) REFERENCES users(user_id);
ALTER TABLE trips ADD CONSTRAINT fk_trips_origin_city_id FOREIGN KEY (origin_city_id) REFERENCES cities(city_id);
ALTER TABLE trips ADD CONSTRAINT fk_trips_destination_city_id FOREIGN KEY (destination_city_id) REFERENCES cities(city_id);
ALTER TABLE trips ADD CONSTRAINT fk_trips_home_currency FOREIGN KEY (home_currency) REFERENCES currencies(iso4217);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_user_id FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_guide_language FOREIGN KEY (guide_language) REFERENCES languages(bcp47);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_preferred_currency FOREIGN KEY (preferred_currency) REFERENCES currencies(iso4217);
ALTER TABLE user_preferences ADD CONSTRAINT fk_user_preferences_max_daily_budget_currency FOREIGN KEY (max_daily_budget_currency) REFERENCES currencies(iso4217);
ALTER TABLE hotel_media ADD CONSTRAINT fk_hotel_media_hotel_id FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id);
ALTER TABLE hotel_media ADD CONSTRAINT fk_hotel_media_room_type_id FOREIGN KEY (room_type_id) REFERENCES hotel_room_types(room_type_id);
ALTER TABLE itineraries ADD CONSTRAINT fk_itineraries_trip_id FOREIGN KEY (trip_id) REFERENCES trips(trip_id);
ALTER TABLE itineraries ADD CONSTRAINT fk_itineraries_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE itinerary_items ADD CONSTRAINT fk_itinerary_items_itinerary_id FOREIGN KEY (itinerary_id) REFERENCES itineraries(itinerary_id);
ALTER TABLE itinerary_items ADD CONSTRAINT fk_itinerary_items_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);
ALTER TABLE bookings ADD CONSTRAINT fk_bookings_user_id FOREIGN KEY (user_id) REFERENCES users(user_id);
ALTER TABLE bookings ADD CONSTRAINT fk_bookings_trip_id FOREIGN KEY (trip_id) REFERENCES trips(trip_id);
ALTER TABLE bookings ADD CONSTRAINT fk_bookings_itinerary_id FOREIGN KEY (itinerary_id) REFERENCES itineraries(itinerary_id);
ALTER TABLE bookings ADD CONSTRAINT fk_bookings_currency FOREIGN KEY (currency) REFERENCES currencies(iso4217);

-- indexes
CREATE INDEX idx_categories_parent_category_id ON categories(parent_category_id);
CREATE INDEX idx_price_history_currency ON price_history(currency);
CREATE INDEX idx_countries_default_currency ON countries(default_currency);
CREATE INDEX idx_cities_country_id ON cities(country_id);
CREATE INDEX idx_cities_primary_language ON cities(primary_language);
CREATE INDEX idx_hotels_city_id ON hotels(city_id);
CREATE INDEX idx_hotels_base_currency ON hotels(base_currency);
CREATE INDEX idx_tour_guides_city_id ON tour_guides(city_id);
CREATE INDEX idx_tour_guides_currency ON tour_guides(currency);
CREATE INDEX idx_tour_packages_city_id ON tour_packages(city_id);
CREATE INDEX idx_tour_packages_currency ON tour_packages(currency);
CREATE INDEX idx_transfers_city_id ON transfers(city_id);
CREATE INDEX idx_transfers_currency ON transfers(currency);
CREATE INDEX idx_users_home_city_id ON users(home_city_id);
CREATE INDEX idx_users_home_currency ON users(home_currency);
CREATE INDEX idx_users_locale ON users(locale);
CREATE INDEX idx_guide_availability_guide_id ON guide_availability(guide_id);
CREATE INDEX idx_hotel_room_types_hotel_id ON hotel_room_types(hotel_id);
CREATE INDEX idx_hotel_room_types_currency ON hotel_room_types(currency);
CREATE INDEX idx_package_components_package_id ON package_components(package_id);
CREATE INDEX idx_package_components_currency ON package_components(currency);
CREATE INDEX idx_trips_owner_user_id ON trips(owner_user_id);
CREATE INDEX idx_trips_origin_city_id ON trips(origin_city_id);
CREATE INDEX idx_trips_destination_city_id ON trips(destination_city_id);
CREATE INDEX idx_trips_home_currency ON trips(home_currency);
CREATE INDEX idx_user_preferences_guide_language ON user_preferences(guide_language);
CREATE INDEX idx_user_preferences_preferred_currency ON user_preferences(preferred_currency);
CREATE INDEX idx_user_preferences_max_daily_budget_currency ON user_preferences(max_daily_budget_currency);
CREATE INDEX idx_hotel_media_hotel_id ON hotel_media(hotel_id);
CREATE INDEX idx_hotel_media_room_type_id ON hotel_media(room_type_id);
CREATE INDEX idx_itineraries_trip_id ON itineraries(trip_id);
CREATE INDEX idx_itineraries_currency ON itineraries(currency);
CREATE INDEX idx_itinerary_items_itinerary_id ON itinerary_items(itinerary_id);
CREATE INDEX idx_itinerary_items_currency ON itinerary_items(currency);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_trip_id ON bookings(trip_id);
CREATE INDEX idx_bookings_itinerary_id ON bookings(itinerary_id);
CREATE INDEX idx_bookings_currency ON bookings(currency);