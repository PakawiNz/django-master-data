import os

from django.apps import apps
from django.core.management import BaseCommand, call_command
from django.core.serializers import sort_dependencies


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'args', metavar='app_label', nargs='*',
            help='Restricts dumped data to the specified app_label.',
        )

    def handle(self, *app_labels, **options):
        for app_label in app_labels:
            path = os.path.join(app_label, 'data')

            models = [
                apps.get_registered_model(*os.path.splitext(file)[0].split('.'))
                for top, dirs, files in os.walk(path)
                for file in files
            ]

            apps_models = {}
            for model in models:
                apps_models.setdefault(model._meta.app_label, []).append(model)

            apps_models = [
                (apps.get_app_config(app_label), models)
                for app_label, models in apps_models.items()
            ]

            models = sort_dependencies(apps_models)
            for model in models:
                file = '{}.{}.json'.format(model._meta.app_label, model._meta.model_name)
                call_command(
                    'loaddata',
                    os.path.join(path, file),
                )
