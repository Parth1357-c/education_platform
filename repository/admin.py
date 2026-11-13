from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Chapter, Profile, Doubt, TeacherInbox, PaymentTransaction, AIResponseCache, ScheduledClass

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_level', 'subject', 'created_at']
    list_filter = ['class_level', 'subject', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    list_per_page = 20


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'tier_badge', 'is_paid', 'total_doubts', 'created_at']
    list_filter = ['is_paid', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_editable = ['is_paid']
    readonly_fields = ['total_doubts', 'created_at', 'updated_at']
    list_per_page = 20
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}" style="color: #00f5d4;">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def tier_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="background: linear-gradient(135deg, #00f5d4, #9b5de5); padding: 4px 12px; border-radius: 20px; font-weight: bold; color: #0a0a0a;">⭐ PREMIUM</span>')
        return format_html('<span style="background: rgba(139, 139, 154, 0.2); padding: 4px 12px; border-radius: 20px; color: #8a8a9a;">🆓 Free</span>')
    tier_badge.short_description = 'Tier'
    
    actions = ['upgrade_to_premium', 'downgrade_to_free']
    
    def upgrade_to_premium(self, request, queryset):
        count = queryset.update(is_paid=True)
        self.message_user(request, f'✅ {count} user(s) upgraded to Premium!')
    upgrade_to_premium.short_description = 'Upgrade selected to Premium'
    
    def downgrade_to_free(self, request, queryset):
        count = queryset.update(is_paid=False)
        self.message_user(request, f'🆓 {count} user(s) downgraded to Free')
    downgrade_to_free.short_description = 'Downgrade selected to Free'


@admin.register(Doubt)
class DoubtAdmin(admin.ModelAdmin):
    list_display = ['id', 'student_link', 'query_preview', 'category_badge', 'mode', 'priority', 'created_at']
    list_filter = ['mode', 'priority', 'created_at']
    search_fields = ['student__username', 'query']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    def student_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.student.id])
        return format_html('<a href="{}" style="color: #00f5d4;">{}</a>', url, obj.student.username)
    student_link.short_description = 'Student'
    
    def query_preview(self, obj):
        if len(obj.query) > 60:
            return obj.query[:60] + '...'
        return obj.query
    query_preview.short_description = 'Question'
    
    def category_badge(self, obj):
        colors = {
            'PYTHON': '#00f5d4',
            'SQL': '#00bbf9',
            'NETWORKING': '#9b5de5',
            'DSA': '#fb5607',
            'WEB': '#fee440',
            'OOPS': '#ff006e',
        }
        color = colors.get(obj.category, '#8a8a9a')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_category_display())
    category_badge.short_description = 'Category'


@admin.register(TeacherInbox)
class TeacherInboxAdmin(admin.ModelAdmin):
    list_display = ['id', 'doubt_link', 'student_name', 'status', 'response_sent']
    list_filter = ['status', 'response_sent']
    search_fields = ['doubt__student__username']
    readonly_fields = ['created_at']
    list_per_page = 20
    
    def doubt_link(self, obj):
        url = reverse('admin:repository_doubt_change', args=[obj.doubt.id])
        return format_html('<a href="{}" style="color: #00f5d4;">Doubt #{}</a>', url, obj.doubt.id)
    doubt_link.short_description = 'Doubt'
    
    def student_name(self, obj):
        return obj.doubt.student.username
    student_name.short_description = 'Student'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'amount', 'transaction_id', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'transaction_id']
    readonly_fields = ['transaction_id', 'created_at']
    list_per_page = 20
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}" style="color: #00f5d4;">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    actions = ['verify_payments']
    
    def verify_payments(self, request, queryset):
        count = 0
        for payment in queryset.filter(status='PENDING'):
            payment.verify_payment(request.user)
            count += 1
        self.message_user(request, f'✅ {count} payment(s) verified!')
    verify_payments.short_description = 'Verify selected payments'


@admin.register(AIResponseCache)
class AIResponseCacheAdmin(admin.ModelAdmin):
    list_display = ['query_preview', 'ai_model', 'access_count', 'created_at']
    list_filter = ['ai_model', 'created_at']
    search_fields = ['query_text']
    readonly_fields = ['query_hash', 'created_at']
    list_per_page = 20
    
    def query_preview(self, obj):
        if len(obj.query_text) > 50:
            return obj.query_text[:50] + '...'
        return obj.query_text
    query_preview.short_description = 'Query'

@admin.register(ScheduledClass)
class ScheduledClassAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'date', 'start_time', 'end_time', 'status', 'get_enrolled_count']
    list_filter = ['status', 'date', 'teacher']
    search_fields = ['title', 'description']
    filter_horizontal = ['enrolled_students']
    
    def get_enrolled_count(self, obj):
        return obj.get_enrolled_count()
    get_enrolled_count.short_description = 'Enrolled Students'
admin.site.site_header = "CS WITH HIMANSHU GOYAL"
admin.site.site_title = "Neural Admin Panel"
admin.site.index_title = "Core-Sage Dashboard"
