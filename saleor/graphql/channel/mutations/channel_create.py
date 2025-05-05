import graphene
from django.utils.text import slugify

from ....channel import models
from ....core.tracing import traced_atomic_transaction
from ....permission.enums import ChannelPermissions
from ....webhook.event_types import WebhookEventAsyncType
from ...account.enums import CountryCodeEnum
from ...core import ResolveInfo
from ...core.descriptions import (
    ADDED_IN_31,
    ADDED_IN_35,
    ADDED_IN_37,
    ADDED_IN_312,
    ADDED_IN_313,
    ADDED_IN_314,
    ADDED_IN_315,
    ADDED_IN_316,
    ADDED_IN_318,
    ADDED_IN_320,
    DEPRECATED_IN_3X_INPUT,
    PREVIEW_FEATURE,
)
from ...core.doc_category import (
    DOC_CATEGORY_CHANNELS,
)
from ...core.mutations import ModelMutation
from ...core.scalars import Day, Minute
from ...core.types import BaseInputObjectType, ChannelError, NonNullList
from ...core.types import common as common_types
from ...core.utils import WebhookEventInfo
from ...meta.inputs import MetadataInput
from ...plugins.dataloaders import get_plugin_manager_promise
from ..enums import (
    AllocationStrategyEnum,
    MarkAsPaidStrategyEnum,
)
from ..types import Channel
from .utils import (
    clean_input_checkout_settings,
    clean_input_order_settings,
    clean_input_payment_settings,
)


class ChannelInput(BaseInputObjectType):
    is_active = graphene.Boolean(
        description="Determine if channel will be set active or not."
    )
    metadata = common_types.NonNullList(
        MetadataInput,
        description="Channel public metadata." + ADDED_IN_315,
        required=False,
    )
    private_metadata = common_types.NonNullList(
        MetadataInput,
        description="Channel private metadata." + ADDED_IN_315,
        required=False,
    )

    class Meta:
        doc_category = DOC_CATEGORY_CHANNELS


class ChannelCreateInput(ChannelInput):
    name = graphene.String(description="Name of the channel.", required=True)
    slug = graphene.String(description="Slug of the channel.", required=True)
    currency_code = graphene.String(
        description="Currency of the channel.", required=True
    )
    default_country = CountryCodeEnum(
        description=(
            "Default country for the channel. Default country can be "
            "used in checkout to determine the stock quantities or calculate taxes "
            "when the country was not explicitly provided." + ADDED_IN_31
        ),
        required=True,
    )

    class Meta:
        doc_category = DOC_CATEGORY_CHANNELS


class ChannelCreate(ModelMutation):
    class Arguments:
        input = ChannelCreateInput(
            required=True, description="Fields required to create channel."
        )

    class Meta:
        description = "Creates new channel."
        model = models.Channel
        object_type = Channel
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"
        webhook_events_info = [
            WebhookEventInfo(
                type=WebhookEventAsyncType.CHANNEL_CREATED,
                description="A channel was created.",
            ),
        ]
        support_meta_field = True
        support_private_meta_field = True

    @classmethod
    def get_type_for_model(cls):
        return Channel

    @classmethod
    def clean_input(cls, info: ResolveInfo, instance, data, **kwargs):
        cleaned_input = super().clean_input(info, instance, data, **kwargs)
        slug = cleaned_input.get("slug")
        if slug:
            cleaned_input["slug"] = slugify(slug)
        if stock_settings := cleaned_input.get("stock_settings"):
            cleaned_input["allocation_strategy"] = stock_settings["allocation_strategy"]
        if order_settings := cleaned_input.get("order_settings"):
            clean_input_order_settings(order_settings, cleaned_input, instance)

        if checkout_settings := cleaned_input.get("checkout_settings"):
            clean_input_checkout_settings(checkout_settings, cleaned_input)

        if payment_settings := cleaned_input.get("payment_settings"):
            clean_input_payment_settings(payment_settings, cleaned_input)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info: ResolveInfo, instance, cleaned_data):
        with traced_atomic_transaction():
            super()._save_m2m(info, instance, cleaned_data)
            shipping_zones = cleaned_data.get("add_shipping_zones")
            if shipping_zones:
                instance.shipping_zones.add(*shipping_zones)
            warehouses = cleaned_data.get("add_warehouses")
            if warehouses:
                instance.warehouses.add(*warehouses)

    @classmethod
    def post_save_action(cls, info: ResolveInfo, instance, cleaned_input):
        manager = get_plugin_manager_promise(info.context).get()
        cls.call_event(manager.channel_created, instance)
