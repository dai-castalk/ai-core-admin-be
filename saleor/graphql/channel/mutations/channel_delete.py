from typing import Optional

import graphene
from django.core.exceptions import ValidationError

from ....channel import models
from ....channel.error_codes import ChannelErrorCode
from ....permission.enums import ChannelPermissions
from ....webhook.event_types import WebhookEventAsyncType
from ...core import ResolveInfo
from ...core.doc_category import DOC_CATEGORY_CHANNELS
from ...core.mutations import ModelDeleteMutation
from ...core.types import BaseInputObjectType, ChannelError
from ...core.utils import WebhookEventInfo
from ...plugins.dataloaders import get_plugin_manager_promise
from ..types import Channel


class ChannelDeleteInput(BaseInputObjectType):
    channel_id = graphene.ID(
        required=True,
        description="ID of channel to migrate orders from origin channel.",
    )

    class Meta:
        doc_category = DOC_CATEGORY_CHANNELS


class ChannelDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a channel to delete.")
        input = ChannelDeleteInput(description="Fields required to delete a channel.")

    class Meta:
        description = (
            "Delete a channel. Orders associated with the deleted "
            "channel will be moved to the target channel. "
            "Checkouts, product availability, and pricing will be removed."
        )
        model = models.Channel
        object_type = Channel
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"
        webhook_events_info = [
            WebhookEventInfo(
                type=WebhookEventAsyncType.CHANNEL_DELETED,
                description="A channel was deleted.",
            ),
        ]

    @classmethod
    def validate_input(cls, origin_channel, target_channel):
        if origin_channel.id == target_channel.id:
            raise ValidationError(
                {
                    "channel_id": ValidationError(
                        "Cannot migrate data to the channel that is being removed.",
                        code=ChannelErrorCode.INVALID.value,
                    )
                }
            )
        origin_channel_currency = origin_channel.currency_code
        target_channel_currency = target_channel.currency_code
        if origin_channel_currency != target_channel_currency:
            raise ValidationError(
                {
                    "channel_id": ValidationError(
                        f"Cannot migrate from {origin_channel_currency} "
                        f"to {target_channel_currency}. "
                        "Migration are allowed between the same currency",
                        code=ChannelErrorCode.CHANNELS_CURRENCY_MUST_BE_THE_SAME.value,
                    )
                }
            )

    @classmethod
    def post_save_action(cls, info: ResolveInfo, instance, cleaned_input):
        manager = get_plugin_manager_promise(info.context).get()
        cls.call_event(manager.channel_deleted, instance)

    @classmethod
    def perform_mutation(  # type: ignore[override]
        cls, root, info: ResolveInfo, /, *, id: str, input: Optional[dict] = None
    ):
        return super().perform_mutation(root, info, id=id)
