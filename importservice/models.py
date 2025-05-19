from django.db import models

# Create your models here.
from django.contrib.gis.db import models
import uuid

class product_index(models.Model):
    area = models.MultiPolygonField()
    metadataid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    date = models.DateField()
    scale = models.IntegerField()
    file_path = models.FilePathField(path='.')
    def __str__(self):
        return f"{self.metadataid}: {self.file_path}" 