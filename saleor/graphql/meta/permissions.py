from typing import Any, Callable, Union

from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef

from ...account import models as account_models
from ...account.error_codes import AccountErrorCode
from ...core.exceptions import PermissionDenied
from ...core.jwt import JWT_THIRDPARTY_ACCESS_TYPE
from ...permission.enums import (
    AccountPermissions,
    AppPermission,
    BasePermissionEnum,
    ChannelPermissions,
)
from ..app.dataloaders import get_app_promise
from ..core import ResolveInfo
from ..core.context import get_database_connection_name
from ..core.utils import from_global_id_or_error


def no_permissions(_info: ResolveInfo, _object_pk: Any) -> list[BasePermissionEnum]:
    return []


def public_user_permissions(
    info: ResolveInfo, user_pk: int
) -> list[BasePermissionEnum]:
    """Resolve permission for access to public metadata for user.

    Customer have access to own public metadata.
    Staff user with `MANAGE_USERS` have access to customers public metadata.
    Staff user with `MANAGE_STAFF` have access to staff users public metadata.
    """
    database_connection_name = get_database_connection_name(info.context)
    user = (
        account_models.User.objects.using(database_connection_name)
        .filter(pk=user_pk)
        .first()
    )
    if not user:
        raise ValidationError(
            {
                "id": ValidationError(
                    "Couldn't resolve user.", code=AccountErrorCode.NOT_FOUND.value
                )
            }
        )
    if info.context.user and info.context.user.pk == user.pk:
        return []
    if user.is_staff:
        return [AccountPermissions.MANAGE_STAFF]
    return [AccountPermissions.MANAGE_USERS]


def private_user_permissions(
    info: ResolveInfo, user_pk: int
) -> list[BasePermissionEnum]:
    database_connection_name = get_database_connection_name(info.context)
    user = (
        account_models.User.objects.using(database_connection_name)
        .filter(pk=user_pk)
        .first()
    )
    if not user:
        raise PermissionDenied()
    if user.is_staff:
        return [AccountPermissions.MANAGE_STAFF]
    return [AccountPermissions.MANAGE_USERS]


def public_address_permissions(
    info: ResolveInfo, address_pk: int
) -> list[BasePermissionEnum]:
    """Resolve permission for access to public metadata for user addresses.

    Customer have access to the public metadata of their own addresses.
    Staff user with `MANAGE_USERS` have access to public metadata of customer
    addresses.
    Staff user with `MANAGE_STAFF` have access to public metadata of staff user
    addresses.
    For now, updating warehouse and shop addresses is forbidden.
    """
    database_connection_name = get_database_connection_name(info.context)
    address = (
        account_models.Address.objects.using(database_connection_name)
        .filter(pk=address_pk)
        .prefetch_related("user_addresses")
        .first()
    )
    if not address:
        raise ValidationError(
            {
                "id": ValidationError(
                    "Couldn't resolve address.", code=AccountErrorCode.NOT_FOUND.value
                )
            }
        )
    user = info.context.user
    # no permission is required when the requestor is the owner of the address
    if user and address.user_addresses.filter(id=user.id):
        return []
    staff_users = account_models.User.objects.filter(is_staff=True)

    if address.user_addresses.filter(Exists(staff_users.filter(id=OuterRef("id")))):
        return [AccountPermissions.MANAGE_STAFF]

    return [AccountPermissions.MANAGE_USERS]


def private_address_permissions(
    info: ResolveInfo, address_pk: int
) -> list[BasePermissionEnum]:
    database_connection_name = get_database_connection_name(info.context)
    address = (
        account_models.Address.objects.using(database_connection_name)
        .filter(pk=address_pk)
        .prefetch_related("user_addresses")
        .first()
    )
    if not address:
        raise ValidationError(
            {
                "id": ValidationError(
                    "Couldn't resolve address.", code=AccountErrorCode.NOT_FOUND.value
                )
            }
        )
    staff_users = account_models.User.objects.using(database_connection_name).filter(
        is_staff=True
    )
    if address.user_addresses.filter(Exists(staff_users.filter(id=OuterRef("id")))):
        return [AccountPermissions.MANAGE_STAFF]
    return [AccountPermissions.MANAGE_USERS]


def app_permissions(info: ResolveInfo, object_pk: str) -> list[BasePermissionEnum]:
    auth_token = info.context.decoded_auth_token or {}
    app = get_app_promise(info.context).get()
    app_id: Union[str, int, None]
    if auth_token.get("type") == JWT_THIRDPARTY_ACCESS_TYPE:
        _, app_id = from_global_id_or_error(auth_token["app"], "App")
    else:
        app_id = app.id if app else None
    if app_id is not None and int(app_id) == int(object_pk):
        return []
    return [AppPermission.MANAGE_APPS]


def private_app_permssions(
    info: ResolveInfo, object_pk: str
) -> list[BasePermissionEnum]:
    app = get_app_promise(info.context).get()
    if app and app.pk == int(object_pk):
        return []
    return [AppPermission.MANAGE_APPS]


def channel_permissions(
    _info: ResolveInfo, _object_pk: Any
) -> list[BasePermissionEnum]:
    return [ChannelPermissions.MANAGE_CHANNELS]

PUBLIC_META_PERMISSION_MAP: dict[
    str, Callable[[ResolveInfo, Any], list[BasePermissionEnum]]
] = {
    "Address": public_address_permissions,
    "App": app_permissions,
    "Channel": channel_permissions,
    "User": public_user_permissions,
}


PRIVATE_META_PERMISSION_MAP: dict[
    str, Callable[[ResolveInfo, Any], list[BasePermissionEnum]]
] = {
    "Address": private_address_permissions,
    "App": private_app_permssions,
    "Channel": channel_permissions,
    "User": private_user_permissions,
}
