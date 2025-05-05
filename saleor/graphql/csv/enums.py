from ...csv import ExportEvents, FileTypes
from ..core.enums import to_enum
from ..core.types import BaseEnum

ExportEventEnum = to_enum(ExportEvents)
FileTypeEnum = to_enum(FileTypes)


class ExportScope(BaseEnum):
    ALL = "all"
    IDS = "ids"
    FILTER = "filter"

    @property
    def description(self):
        # pylint: disable=no-member
        description_mapping = {
            ExportScope.ALL.name: "Export all products.",  # type: ignore[attr-defined] # graphene.Enum is not typed # noqa: E501
            ExportScope.IDS.name: "Export products with given ids.",  # type: ignore[attr-defined] # graphene.Enum is not typed # noqa: E501
            ExportScope.FILTER.name: "Export the filtered products.",  # type: ignore[attr-defined] # graphene.Enum is not typed # noqa: E501
        }
        if self.name in description_mapping:
            return description_mapping[self.name]
        raise ValueError(f"Unsupported enum value: {self.value}")
