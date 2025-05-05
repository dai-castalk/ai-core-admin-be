import graphene
from django_prices.templatetags import prices

from ....core.prices import quantize_price
from ...core.types import BaseObjectType


class Money(graphene.ObjectType):
    currency = graphene.String(description="Currency code.", required=True)
    amount = graphene.Float(description="Amount of money.", required=True)

    class Meta:
        description = "Represents amount of money in specific currency."

    @staticmethod
    def resolve_amount(root, _info):
        return quantize_price(root.amount, root.currency)

    @staticmethod
    def resolve_localized(root, _info):
        return prices.amount(root)


class MoneyRange(graphene.ObjectType):
    start = graphene.Field(Money, description="Lower bound of a price range.")
    stop = graphene.Field(Money, description="Upper bound of a price range.")

    class Meta:
        description = "Represents a range of amounts of money."


class TaxedMoney(graphene.ObjectType):
    currency = graphene.String(description="Currency code.", required=True)
    gross = graphene.Field(
        Money, description="Amount of money including taxes.", required=True
    )
    net = graphene.Field(
        Money, description="Amount of money without taxes.", required=True
    )
    tax = graphene.Field(Money, description="Amount of taxes.", required=True)

    class Meta:
        description = (
            "Represents a monetary value with taxes. In cases where taxes were not "
            "applied, net and gross values will be equal."
        )


class TaxedMoneyRange(graphene.ObjectType):
    start = graphene.Field(TaxedMoney, description="Lower bound of a price range.")
    stop = graphene.Field(TaxedMoney, description="Upper bound of a price range.")

    class Meta:
        description = "Represents a range of monetary values."
