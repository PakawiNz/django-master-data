import os
from typing import Type

from django.apps import apps
from django.core.management import BaseCommand, call_command
from django.db.models import Q

from ...models import MasterDataModelMixin


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='app_label', nargs='*',
            help='Restricts dumped data to the specified app_label.',
        )

    def handle(self, *app_labels, **options):
        for app_label in app_labels:
            path = os.path.join(app_label, 'data')
            if not os.path.exists(path):
                os.makedirs(path)
            app_config = apps.get_app_config(app_label)
            app_models = app_config.get_models()
            models = {}

            def update_related_models(model: Type[MasterDataModelMixin], filtering=None, related_field=None, related_q=None, stack=None, ):
                if not issubclass(model, MasterDataModelMixin):
                    return
                if not stack:
                    stack = tuple()

                model_name = model.__name__
                app_model_name = '{}.{}'.format(model._meta.app_label, model_name)

                if app_model_name not in models:
                    models[app_model_name] = set()

                if related_field and models[app_model_name] is not None:
                    keys = set(related_field.model.objects.filter(related_q).distinct().values_list(related_field.name, flat=True))
                    models[app_model_name].update(filter(None, keys))

                elif filtering and models[app_model_name] is not None:
                    keys = set(model.objects.filter(**filtering).distinct().values_list('pk', flat=True))
                    models[app_model_name].update(filter(None, keys))

                else:
                    models[app_model_name] = None

                if models[app_model_name] is not None:
                    related_q = Q(pk__in=models[app_model_name])
                else:
                    related_q = Q()

                for field in model._meta.get_fields():
                    if not field.related_model:
                        continue
                    if field.related_model in stack:
                        continue

                    update_related_models(
                        field.related_model,
                        related_field=field,
                        related_q=related_q,
                        stack=stack + (model,),
                    )

            for model in app_models:
                update_related_models(model)

            for model_name in getattr(app_config, 'preload_data', []):
                update_related_models(apps.get_model(*model_name.split('.')), filtering=app_config.preload_data[model_name])

            for app_model_name, keys in models.items():
                if keys is None:
                    keys = None
                elif len(keys):
                    keys = ','.join(map(str, keys))
                else:
                    continue

                call_command(
                    'dumpdata',
                    app_model_name,
                    indent=2,
                    output=os.path.join(path, '{}.json'.format(app_model_name.lower())),
                    primary_keys=keys,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=True,
                )
