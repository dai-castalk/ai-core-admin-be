from ...webhook.event_types import WebhookEventAsyncType
from ..core import ResolveInfo
from ..plugins.dataloaders import get_plugin_manager_promise


def extra_channel_actions(instance, info: ResolveInfo, **data):
    manager = get_plugin_manager_promise(info.context).get()
    manager.channel_metadata_updated(instance)

def extra_user_actions(instance, info: ResolveInfo, **data):
    manager = get_plugin_manager_promise(info.context).get()
    manager.customer_updated(instance)
    manager.customer_metadata_updated(instance)


TYPE_EXTRA_METHODS = {
    "Channel": extra_channel_actions,
    "User": extra_user_actions,
}


TYPE_EXTRA_PREFETCH = {
}
