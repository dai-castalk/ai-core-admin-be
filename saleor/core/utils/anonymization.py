import copy
import logging
from typing import TYPE_CHECKING

from faker import Faker

from ...account.models import Address, User
from .random_data import create_address, create_fake_user

logger = logging.getLogger(__name__)

fake = Faker()


def _fake_save(*args, **kwargs):
    logger.error("Unable to save fake instance")


def generate_fake_address() -> "Address":
    """Generate a fake instance of the "Address" class.

    The instance cannot be saved
    """
    fake_address = create_address(save=False)
    # Prevent accidental saving of the instance
    fake_address.save = _fake_save
    return fake_address


def generate_fake_user() -> "User":
    """Generate a fake instance of the "User" class.

    The instance cannot be saved
    """
    fake_user = create_fake_user(user_password=None, save=False, generate_id=True)
    # Prevent accidental saving of the instance
    fake_user.save = _fake_save
    return fake_user


def generate_fake_metadata() -> dict[str, str]:
    """Generate a fake metadata/private metadata dictionary."""
    return fake.pydict(value_types=str)
