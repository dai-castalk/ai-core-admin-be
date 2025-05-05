import graphene

from .mutations import FileUpload


class CoreMutations(graphene.ObjectType):
    file_upload = FileUpload.Field()
