from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# ========== CHAPTER MODEL ==========

class Chapter(models.Model):
    CLASS_CHOICES = [
        ('11', 'Class 11'),
        ('12', 'Class 12'),
    ]
    
    SUBJECT_CHOICES = [
        ('CS', 'Computer Science'),
        ('IP', 'Informatics Practices'),
    ]
    
    title = models.CharField(max_length=200)
    class_level = models.CharField(
        max_length=2,
        choices=CLASS_CHOICES,
        default='11',
        help_text="Select Class 11 or 12"
    )
    subject = models.CharField(
        max_length=2,
        choices=SUBJECT_CHOICES,
        default='CS',
        help_text="Select Computer Science or Informatics Practices"
    )
    description = models.TextField(blank=True, help_text="Brief description of the chapter content")
    notes_file = models.FileField(
        upload_to='notes/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF notes file",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'
    
    def __str__(self):
        return f"{self.title} (Class {self.class_level} - {self.subject})"


# ========== PROFILE MODEL ==========

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_paid = models.BooleanField(default=False, help_text="Premium tier access status")
    bio = models.TextField(blank=True, help_text="User biography or introduction")
    total_doubts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {'Paid' if self.is_paid else 'Free'} User"
    
    def increment_doubt_count(self):
        self.total_doubts += 1
        self.save()


# ========== DOUBT MODEL ==========

class Doubt(models.Model):
    MODE_CHOICES = [
        ('FREE_AI', 'Free AI (Basic)'),
        ('PAID_AI', 'Premium AI (Advanced)'),
        ('TEACHER', 'Faculty Direct - Command Uplink'),
    ]
    
    PRIORITY_CHOICES = [
        (0, 'Low Priority'),
        (1, 'Normal Priority'),
        (2, 'High Priority'),
        (3, 'Urgent Priority'),
    ]
    
    CATEGORY_CHOICES = [
        ('PYTHON', '🐍 Python'),
        ('SQL', '📊 SQL/Database'),
        ('NETWORKING', '🌐 Networking'),
        ('DSA', '📈 Data Structures & Algorithms'),
        ('WEB', '🌍 Web Development'),
        ('OOPS', '🎭 OOP Concepts'),
        ('FILE_HANDLING', '📁 File Handling'),
        ('ERRORS', '⚠️ Error Debugging'),
        ('CS_GENERAL', '💻 Computer Science General'),
        ('IP_GENERAL', '📱 Informatics Practices'),
        ('OTHER', '❓ Other'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doubts')
    query = models.TextField(help_text="Student's question or doubt")
    response = models.TextField(blank=True, null=True, help_text="AI or Faculty response")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='FREE_AI')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER', help_text="Select the category of your doubt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    ai_model_used = models.CharField(max_length=50, blank=True, null=True)
    response_time_ms = models.IntegerField(blank=True, null=True)
    tokens_used = models.IntegerField(blank=True, null=True)
    is_escalated = models.BooleanField(default=False)
    satisfaction_rating = models.IntegerField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Doubt'
        verbose_name_plural = 'Doubts'
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.get_mode_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def resolve(self):
        self.resolved_at = timezone.now()
        self.save()
    
    @property
    def is_resolved(self):
        return self.resolved_at is not None


# ========== TEACHER INBOX MODEL ==========

class TeacherInbox(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_PROGRESS', 'Being Addressed'),
        ('RESOLVED', 'Resolved'),
        ('ESCALATED', 'Escalated to Senior Faculty'),
    ]
    
    doubt = models.OneToOneField(Doubt, on_delete=models.CASCADE, related_name='teacher_inbox')
    is_resolved = models.BooleanField(default=False)
    teacher_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_doubts', limit_choices_to={'is_staff': True})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    response_sent = models.BooleanField(default=False)
    response_sent_at = models.DateTimeField(blank=True, null=True)
    faculty_response = models.TextField(blank=True)
    email_notification_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Teacher Inbox'
        verbose_name_plural = 'Teacher Inboxes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Inbox: {self.doubt.student.username} - {self.get_status_display()}"
    
    def mark_resolved(self):
        self.is_resolved = True
        self.status = 'RESOLVED'
        self.response_sent = True
        self.response_sent_at = timezone.now()
        self.save()
        self.doubt.resolve()


# ========== PAYMENT TRANSACTION MODEL ==========

class PaymentTransaction(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending Verification'),
        ('COMPLETED', 'Payment Completed'),
        ('FAILED', 'Payment Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=499.00)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50, default='QR_CODE')
    qr_code_url = models.URLField(blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments', limit_choices_to={'is_staff': True})
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"
    
    def verify_payment(self, staff_user):
        self.status = 'COMPLETED'
        self.verified_by = staff_user
        self.verified_at = timezone.now()
        self.save()
        self.user.profile.is_paid = True
        self.user.profile.save()


# ========== AI RESPONSE CACHE MODEL ==========

class AIResponseCache(models.Model):
    query_hash = models.CharField(max_length=64, unique=True)
    query_text = models.TextField()
    response_text = models.TextField()
    ai_model = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    access_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'AI Response Cache'
        verbose_name_plural = 'AI Response Cache'
        ordering = ['-access_count']
    
    def __str__(self):
        return f"Cache: {self.query_hash[:10]}... (Accessed: {self.access_count})"
    
    def increment_access(self):
        self.access_count += 1
        self.save()
class ScheduledClass(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', '📅 Upcoming'),
        ('ONGOING', '🔄 Ongoing'),
        ('COMPLETED', '✅ Completed'),
        ('CANCELLED', '❌ Cancelled'),
    ]
    
    title = models.CharField(max_length=200, help_text="Title of the class")
    description = models.TextField(blank=True, help_text="What will be covered")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classes', limit_choices_to={'is_staff': True})
    date = models.DateField(help_text="Date of the class")
    start_time = models.TimeField(help_text="Start time of the class")
    end_time = models.TimeField(help_text="End time of the class")
    meeting_link = models.URLField(blank=True, help_text="Google Meet / Zoom / Teams link")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    max_students = models.IntegerField(default=50, help_text="Maximum number of students allowed")
    enrolled_students = models.ManyToManyField(User, related_name='enrolled_classes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Scheduled Class'
        verbose_name_plural = 'Scheduled Classes'
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.title} - {self.date} ({self.start_time} - {self.end_time})"
    
    def is_full(self):
        return self.enrolled_students.count() >= self.max_students
    
    def get_enrolled_count(self):
        return self.enrolled_students.count()

# ========== SIGNALS ==========

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, is_paid=False)
        print(f"✅ Profile created for user: {instance.username} (Free Tier)")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(post_save, sender=Doubt)
def create_teacher_inbox(sender, instance, created, **kwargs):
    if created and instance.mode == 'TEACHER':
        TeacherInbox.objects.create(doubt=instance)
        print(f"📬 Teacher inbox created for doubt: {instance.id}")


@receiver(post_save, sender=Doubt)
def increment_profile_doubt_count(sender, instance, created, **kwargs):
    if created:
        instance.student.profile.increment_doubt_count()
