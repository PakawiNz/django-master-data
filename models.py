from django.db import models
from django.utils.decorators import classproperty


class MasterDataModelMixin:
    pass


class NaturalKeyQueryset(models.QuerySet):
    def get_by_natural_key(self, *args):
        kwargs = {}

        def dig_fields(model, data, base_name=''):
            for i, field_name in enumerate(model.natural_key_fields):
                field = model._meta.get_field(field_name)
                related_model = getattr(field, 'related_model', None)
                if related_model and issubclass(related_model, NaturalKeyModelMixin):
                    dig_fields(related_model, data[i], base_name + field_name + '__')
                else:
                    kwargs[base_name + field_name] = data[i]

        dig_fields(self.model, args)
        return self.get(**kwargs)


class NaturalKeyModelMixin(models.Model):
    objects = NaturalKeyQueryset.as_manager()

    @classproperty
    def natural_key_fields(cls):
        if cls._meta.unique_together:
            return cls._meta.unique_together[0]
        for field in cls._meta.get_fields():
            if field.concrete and field.unique and not field.auto_created:
                return [field.name]
        else:
            return []

    def natural_key(self):
        return tuple(
            key.natural_key() if hasattr(key, 'natural_key') else key
            for key in (
                getattr(self, name)
                for name in self.natural_key_fields
            )
        )

    class Meta:
        abstract = True
