locations, total_count = await model_service.list_and_count(
    statement=select(Model).where(ST_DWithin(UniqueLocation.location, geog, 1000)),
    account_id=str(account_id),
)