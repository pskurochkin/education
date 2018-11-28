from django.db import models
from django.contrib.postgres.fields import ArrayField


class Region(models.Model):
    yandex_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class University(models.Model):
    yandex_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=1024, default=None, null=True)
    place = models.IntegerField(default=None, null=True)
    # city = models.CharField(max_length=128, default=None)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Specialty(models.Model):
    yandex_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=128)
    place = models.IntegerField(default=None, null=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Variant(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)
    department = models.CharField(max_length=128, null=True)
    education_type = models.CharField(max_length=128, null=True)
    subjects = models.ManyToManyField(Subject)
    budget_plan = models.IntegerField(null=True)
    budget_passing_score = models.IntegerField(null=True)
    paid_plan = models.IntegerField(null=True)
    paid_passing_score = models.IntegerField(null=True)
    cost = models.IntegerField(null=True)
    rating = models.FloatField(null=True)
    applicants = ArrayField(models.IntegerField(), default=list)

    def __str__(self):
        return self.specialty.name
