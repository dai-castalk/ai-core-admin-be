def metadata_contains_empty_key(metadata_list: list[dict]) -> bool:
    """Check if metadata list contains empty key.

    Deprecated.
    Construct MetadataItemCollection instead, that internally validates metadata structure.
    """
    return not all(data["key"].strip() for data in metadata_list)
