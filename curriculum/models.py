from django.db import models

# Create your models here.


class Note(models.Model):
    CLASS_CHOICES = [('11', 'Class 11'), ('12', 'Class 12')]
    
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=50) # CS or IP
    grade = models.CharField(max_length=2, choices=CLASS_CHOICES)
    is_exclusive = models.BooleanField(default=False) # For member-only notes
    file = models.FileField(upload_to='notes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.grade}"
