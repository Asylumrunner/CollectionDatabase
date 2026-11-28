from dataclasses import fields
from DataClasses.item import Item

REQUIRED_ITEM_FIELDS = ['title', 'media_type', 'release_year', 'img_link', 'original_api_id', 'created_by']


def missing_item_fields(data):
    return [field for field in REQUIRED_ITEM_FIELDS if field not in data]


def item_from_payload(data):
    # Built from the dataclass fields, so a field added to Item is picked up here without another edit.
    # Keys in the body that aren't Item fields are ignored. Assumes missing_item_fields came back empty
    values = {field.name: data.get(field.name) for field in fields(Item)}
    values['id'] = data.get('id', '')
    return Item(**values)


def parse_page(args):
    """Returns the requested page number (1 if none was given), or None if it isn't an integer."""
    try:
        return int(args.get('page', 1))
    except ValueError:
        return None
