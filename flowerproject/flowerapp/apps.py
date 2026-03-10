from django.apps import AppConfig


class FlowerappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flowerapp'


class FlowerappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flowerapp'

    def ready(self):
        from .firebase import initialize_firebase
        initialize_firebase()