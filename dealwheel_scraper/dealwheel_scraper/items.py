import scrapy


class ListingItem(scrapy.Item):
    # identity
    listing_id = scrapy.Field()
    ad_url = scrapy.Field()

    # plain text fields (cleaned in place by CleaningPipeline)
    title = scrapy.Field()
    brand = scrapy.Field()
    model = scrapy.Field()
    city = scrapy.Field()
    fuel_type = scrapy.Field()
    transmission = scrapy.Field()
    color = scrapy.Field()
    body_type = scrapy.Field()
    description = scrapy.Field()
    seller_comments = scrapy.Field()
    registered_in = scrapy.Field()
    assembly = scrapy.Field()
    is_featured = scrapy.Field()

    # raw values as scraped; CleaningPipeline turns these into the typed
    # fields below and does not forward the _raw fields to the DB layer
    year_raw = scrapy.Field()
    mileage_raw = scrapy.Field()
    engine_capacity_raw = scrapy.Field()
    price_raw = scrapy.Field()
    price_currency = scrapy.Field()

    # typed/cleaned fields, populated by CleaningPipeline
    year = scrapy.Field()
    mileage = scrapy.Field()
    engine_capacity = scrapy.Field()
    price = scrapy.Field()

    # list of raw feature strings -> turned into feature_* columns by PostgresPipeline
    features = scrapy.Field()
