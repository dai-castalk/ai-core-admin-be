import json
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Union,
)

import graphene
from django.db.models import F, QuerySet, Sum
from django.utils import timezone
from graphene.utils.str_converters import to_camel_case

from .. import __version__
from ..account.models import User
from ..core.db.connection import allow_writer
from ..core.prices import quantize_price, quantize_price_fields
from ..core.utils import build_absolute_uri
from ..core.utils.anonymization import (
    generate_fake_user,
)
from ..core.utils.json_serializer import CustomJsonEncoder
from ..thumbnail.models import Thumbnail
from . import traced_payload_generator
from .event_types import WebhookEventAsyncType
from .payload_serializers import PayloadSerializer

if TYPE_CHECKING:
    from ..plugins.base_plugin import RequestorOrLazyObject


ADDRESS_FIELDS = (
    "first_name",
    "last_name",
    "company_name",
    "street_address_1",
    "street_address_2",
    "city",
    "city_area",
    "postal_code",
    "country",
    "country_area",
    "phone",
)

CHANNEL_FIELDS = ("slug", "currency_code")

ORDER_FIELDS = (
    "status",
    "origin",
    "shipping_method_name",
    "collection_point_name",
    "shipping_price_net_amount",
    "shipping_price_gross_amount",
    "shipping_tax_rate",
    "weight",
    "language_code",
    "private_metadata",
    "metadata",
    "total_net_amount",
    "total_gross_amount",
    "undiscounted_total_net_amount",
    "undiscounted_total_gross_amount",
)

ORDER_PRICE_FIELDS = (
    "shipping_price_net_amount",
    "shipping_price_gross_amount",
    "total_net_amount",
    "total_gross_amount",
    "undiscounted_total_net_amount",
    "undiscounted_total_gross_amount",
)


def generate_requestor(requestor: Optional["RequestorOrLazyObject"] = None):
    if not requestor:
        return {"id": None, "type": None}
    if isinstance(requestor, User):
        return {"id": graphene.Node.to_global_id("User", requestor.id), "type": "user"}
    return {"id": requestor.name, "type": "app"}  # type: ignore


def generate_meta(*, requestor_data: dict[str, Any], camel_case=False, **kwargs):
    meta_result = {
        "issued_at": timezone.now().isoformat(),
        "version": __version__,
        "issuing_principal": requestor_data,
    }

    meta_result.update(kwargs)

    if camel_case:
        meta = {}
        for key, value in meta_result.items():
            meta[to_camel_case(key)] = value
    else:
        meta = meta_result

    return meta


@allow_writer()
@traced_payload_generator
def generate_metadata_updated_payload(
    instance: Any, requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    pk_field_name = "id"
    return serializer.serialize(
        [instance],
        fields=[],
        pk_field_name=pk_field_name,
        extra_dict_data={
            "meta": generate_meta(requestor_data=generate_requestor(requestor)),
        },
        dump_type_name=False,
    )


def prepare_order_lines_allocations_payload(line):
    warehouse_id_quantity_allocated_map = list(
        line.allocations.values(
            "quantity_allocated", warehouse_id=F("stock__warehouse_id")
        )
    )
    for item in warehouse_id_quantity_allocated_map:
        item["warehouse_id"] = graphene.Node.to_global_id(
            "Warehouse", item["warehouse_id"]
        )
    return warehouse_id_quantity_allocated_map

def _calculate_added(
    previous_catalogue: defaultdict[str, set[str]],
    current_catalogue: defaultdict[str, set[str]],
    key: str,
) -> list[str]:
    return list(current_catalogue[key] - previous_catalogue[key])


def _calculate_removed(
    previous_catalogue: defaultdict[str, set[str]],
    current_catalogue: defaultdict[str, set[str]],
    key: str,
) -> list[str]:
    return _calculate_added(current_catalogue, previous_catalogue, key)


@allow_writer()
@traced_payload_generator
def generate_customer_payload(
    customer: "User", requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    data = serializer.serialize(
        [customer],
        fields=[
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "language_code",
            "private_metadata",
            "metadata",
        ],
        additional_fields={
            "default_shipping_address": (
                lambda c: c.default_shipping_address,
                ADDRESS_FIELDS,
            ),
            "default_billing_address": (
                lambda c: c.default_billing_address,
                ADDRESS_FIELDS,
            ),
            "addresses": (
                lambda c: c.addresses.all(),
                ADDRESS_FIELDS,
            ),
        },
        extra_dict_data={
            "meta": generate_meta(requestor_data=generate_requestor(requestor))
        },
    )
    return data

def _get_sample_object(qs: QuerySet):
    """Return random object from query."""
    random_object = qs.order_by("?").first()
    return random_object

@allow_writer()
@traced_payload_generator
def generate_sample_payload(event_name: str) -> Optional[dict]:
    user_events = [
        WebhookEventAsyncType.CUSTOMER_CREATED,
        WebhookEventAsyncType.CUSTOMER_UPDATED,
    ]

    if event_name in user_events:
        user = generate_fake_user()
        payload = generate_customer_payload(user)
    return json.loads(payload) if payload else None


@allow_writer()
@traced_payload_generator
def generate_thumbnail_payload(thumbnail: Thumbnail):
    thumbnail_id = graphene.Node.to_global_id("Thumbnail", thumbnail.id)
    return json.dumps({"id": thumbnail_id})
