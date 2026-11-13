from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import json
import openai
from .models import Chapter, Profile, Doubt, TeacherInbox, PaymentTransaction, AIResponseCache, ScheduledClass


# ============================================================
# HOME & LIBRARY VIEWS
# ============================================================

def home(request):
    total_chapters = Chapter.objects.count()
    class_11_count = Chapter.objects.filter(class_level='11').count()
    class_12_count = Chapter.objects.filter(class_level='12').count()
    cs_count = Chapter.objects.filter(subject='CS').count()
    ip_count = Chapter.objects.filter(subject='IP').count()
    
    context = {
        'total_chapters': total_chapters,
        'class_11_count': class_11_count,
        'class_12_count': class_12_count,
        'cs_count': cs_count,
        'ip_count': ip_count,
    }
    return render(request, 'home.html', context)


def library(request):
    chapters = Chapter.objects.all()
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class_level', '')
    subject_filter = request.GET.get('subject', '')
    
    if search_query:
        chapters = chapters.filter(title__icontains=search_query) | chapters.filter(description__icontains=search_query)
    
    if class_filter and class_filter in ['11', '12']:
        chapters = chapters.filter(class_level=class_filter)
    
    if subject_filter and subject_filter in ['CS', 'IP']:
        chapters = chapters.filter(subject=subject_filter)
    
    total_results = chapters.count()
    
    context = {
        'chapters': chapters,
        'total_results': total_results,
        'search_query': search_query,
        'class_filter': class_filter,
        'subject_filter': subject_filter,
    }
    return render(request, 'library.html', context)


# ============================================================
# CHATGPT API FUNCTIONS
# ============================================================

# Configure OpenAI
openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)


def call_chatgpt_api(prompt, system_prompt, max_tokens=500):
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    
    if not api_key:
        print("No OpenAI API key found in settings")
        return None
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None


def generate_free_ai_response(query, priority):
    system_prompt = """You are Core-Sage, an analytical AI mentor for CBSE Computer Science and Informatics Practices students (Class 11-12).

Guidelines:
- Keep responses under 300 words
- Provide step-by-step logic explanation
- Do NOT give complete code, only logic and approach
- Use simple, clear language
- End with an upgrade prompt"""

    user_prompt = f"Priority Level: {priority}/3\n\nStudent Question: {query}\n\nPlease provide a step-by-step explanation."
    
    response = call_chatgpt_api(user_prompt, system_prompt, max_tokens=500)
    
    if response:
        return response
    
    return f"Core-Sage Analysis\n\nQuestion: {query[:100]}...\n\nStep-by-Step Logic:\n1. Understand the problem\n2. Break it down\n3. Apply concepts\n4. Test solution\n\nUpgrade to Premium for code examples!"


def generate_premium_ai_response(query, priority):
    system_prompt = """You are Core-Sage Premium, an advanced AI mentor for CBSE Computer Science students.

You MUST provide:
- Complete, detailed explanations
- WORKING code examples in Python
- Time/space complexity analysis
- Multiple solution approaches
- Best practices and common pitfalls"""

    user_prompt = f"Priority Level: {priority}/3\n\nStudent Question: {query}\n\nPlease provide a comprehensive answer."
    
    response = call_chatgpt_api(user_prompt, system_prompt, max_tokens=1000)
    
    if response:
        return response
    
    return f"Core-Sage Premium Analysis\n\nQuestion: {query}\n\nSolution:\n```python\ndef solve(data):\n    result = []\n    for item in data:\n        result.append(item)\n    return result\n```\n\nComplexity: O(n) time\n\nBest practices: Validate input, handle edge cases."


# ============================================================
# LOGIN & REGISTRATION VIEWS
# ============================================================

def login_register_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'login_register.html')


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        from django.contrib.auth import authenticate, login
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful!'})
        else:
            return JsonResponse({'error': 'Invalid username or password'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already taken'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        from django.contrib.auth import login
        login(request, user)
        
        return JsonResponse({'success': True, 'message': 'Account created successfully!'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login/')


# ============================================================
# CORE-SAGE DOUBT ENGINE VIEWS
# ============================================================

@login_required
def ask_core_sage(request):
    context = {
        'is_paid': request.user.profile.is_paid,
        'user_profile': request.user.profile,
    }
    return render(request, 'ask_core_sage.html', context)


@login_required
@require_http_methods(["POST"])
def submit_doubt(request):
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        priority = int(data.get('priority', 1))
        tier = data.get('tier', 'free')
        category = data.get('category', 'OTHER')
        
        if not query:
            return JsonResponse({'error': 'Query cannot be empty'}, status=400)
        
        user_profile = request.user.profile
        is_paid = user_profile.is_paid
        
        if is_paid and tier == 'premium':
            mode = 'PAID_AI'
        else:
            mode = 'FREE_AI'
        
        doubt = Doubt.objects.create(
            student=request.user,
            query=query,
            mode=mode,
            priority=priority,
            category=category,
        )
        
        start_time = timezone.now()
        
        if mode == 'PAID_AI':
            response_text = generate_premium_ai_response(query, priority)
            ai_model = "ChatGPT-Premium"
        else:
            response_text = generate_free_ai_response(query, priority)
            ai_model = "ChatGPT-Free"
        
        end_time = timezone.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        doubt.response = response_text
        doubt.ai_model_used = ai_model
        doubt.response_time_ms = response_time_ms
        doubt.save()
        
        return JsonResponse({
            'success': True,
            'response': response_text,
            'mode': mode,
            'response_time': response_time_ms,
            'doubt_id': doubt.id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def doubt_history(request):
    doubts = Doubt.objects.filter(student=request.user).order_by('-created_at')
    
    category_filter = request.GET.get('category', '')
    if category_filter:
        doubts = doubts.filter(category=category_filter)
    
    paginator = Paginator(doubts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'doubts': page_obj,
        'total_doubts': doubts.count(),
        'resolved_count': doubts.filter(resolved_at__isnull=False).count(),
    }
    return render(request, 'doubt_history.html', context)


@login_required
def doubt_detail(request, doubt_id):
    doubt = get_object_or_404(Doubt, id=doubt_id, student=request.user)
    teacher_response = None
    if hasattr(doubt, 'teacher_inbox'):
        teacher_response = doubt.teacher_inbox
    
    context = {
        'doubt': doubt,
        'teacher_response': teacher_response,
    }
    return render(request, 'doubt_detail.html', context)


# ============================================================
# PAYMENT & UPGRADE VIEWS
# ============================================================

@login_required
def upgrade_to_premium(request):
    if request.user.profile.is_paid:
        messages.info(request, "You are already a Premium user!")
        return redirect('/ask/')
    
    pending_transaction = PaymentTransaction.objects.filter(
        user=request.user,
        status='PENDING'
    ).first()
    
    if not pending_transaction:
        transaction_id = f"TXN{uuid.uuid4().hex[:10].upper()}"
        pending_transaction = PaymentTransaction.objects.create(
            user=request.user,
            amount=499.00,
            transaction_id=transaction_id,
            payment_method='QR_CODE',
            upi_id="cs@himanshu",
            qr_code_url="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa=cs@himanshu&pn=CS%20With%20Himanshu%20Goyal&am=499&cu=INR"
        )
    
    context = {
        'transaction': pending_transaction,
        'amount': 499.00,
        'upi_id': "cs@himanshu",
    }
    return render(request, 'upgrade.html', context)


@login_required
@require_http_methods(["POST"])
def verify_payment(request, transaction_id):
    if request.user.profile.is_paid:
        return JsonResponse({'error': 'Already premium user'}, status=400)
    
    transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id, user=request.user)
    transaction.verify_payment(request.user)
    
    return JsonResponse({
        'success': True,
        'message': 'Payment verified! You are now a Premium user.'
    })


# ============================================================
# TEACHER INBOX VIEWS
# ============================================================

@login_required
def teacher_inbox(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied. Faculty only area.")
        return redirect('home')
    
    pending_doubts = TeacherInbox.objects.filter(status='PENDING').select_related('doubt__student')
    in_progress_doubts = TeacherInbox.objects.filter(status='IN_PROGRESS').select_related('doubt__student')
    resolved_doubts = TeacherInbox.objects.filter(status='RESOLVED').select_related('doubt__student')[:20]
    
    context = {
        'pending_doubts': pending_doubts,
        'in_progress_doubts': in_progress_doubts,
        'resolved_doubts': resolved_doubts,
        'total_pending': pending_doubts.count(),
    }
    return render(request, 'teacher_inbox.html', context)


@login_required
@require_http_methods(["POST"])
def respond_to_doubt(request, inbox_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        faculty_response = data.get('response', '').strip()
        
        inbox = get_object_or_404(TeacherInbox, id=inbox_id)
        
        inbox.faculty_response = faculty_response
        inbox.status = 'RESOLVED'
        inbox.response_sent = True
        inbox.response_sent_at = timezone.now()
        inbox.save()
        
        inbox.doubt.response = faculty_response
        inbox.doubt.resolve()
        inbox.doubt.save()
        
        return JsonResponse({'success': True, 'message': 'Response sent to student'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# USER DASHBOARD VIEWS
# ============================================================

@login_required
def dashboard(request):
    user_profile = request.user.profile
    doubts = Doubt.objects.filter(student=request.user)
    
    total_doubts = doubts.count()
    resolved_doubts = doubts.filter(resolved_at__isnull=False).count()
    pending_doubts = total_doubts - resolved_doubts
    recent_doubts = doubts.order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'is_paid': user_profile.is_paid,
        'total_doubts': total_doubts,
        'resolved_doubts': resolved_doubts,
        'pending_doubts': pending_doubts,
        'recent_doubts': recent_doubts,
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        bio = data.get('bio', '').strip()
        
        user = request.user
        profile = user.profile
        
        if User.objects.exclude(id=user.id).filter(username=username).exists():
            return JsonResponse({'error': 'Username already taken'}, status=400)
        
        if User.objects.exclude(id=user.id).filter(email=email).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        user.username = username
        user.email = email
        user.save()
        
        profile.bio = bio
        profile.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# CLASSES VIEWS
# ============================================================

def classes_list(request):
    """View all scheduled classes"""
    classes = ScheduledClass.objects.all()
    context = {
        'classes': classes,
    }
    return render(request, 'classes.html', context)


@login_required
@require_http_methods(["POST"])
def enroll_class(request, class_id):
    """Enroll student in a class"""
    try:
        class_obj = get_object_or_404(ScheduledClass, id=class_id)
        
        if class_obj.is_full():
            return JsonResponse({'error': 'Class is full!'}, status=400)
        
        if request.user in class_obj.enrolled_students.all():
            return JsonResponse({'error': 'Already enrolled!'}, status=400)
        
        class_obj.enrolled_students.add(request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully enrolled!'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def schedule_class(request):
    """Teacher-only page to schedule a new class"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Teachers only.")
        return redirect('classes')
    return render(request, 'schedule_class.html')


@login_required
@require_http_methods(["POST"])
def api_schedule_class(request):
    """API endpoint to schedule a new class"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        class_obj = ScheduledClass.objects.create(
            title=data.get('title'),
            description=data.get('description', ''),
            teacher=request.user,
            date=data.get('date'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            meeting_link=data.get('meeting_link', ''),
            max_students=int(data.get('max_students', 50))
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Class scheduled successfully!',
            'class_id': class_obj.id
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
@login_required
def python_interpreter(request):
    """Page with built-in Python interpreter"""
    return render(request, 'python_interpreter.html')
# ============================================================
# TEST API ENDPOINTS
# ============================================================

def test_chatgpt(request):
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    
    if not api_key:
        return JsonResponse({
            'error': 'No OPENAI_API_KEY found in settings'
        }, status=400)
    
    result = call_chatgpt_api("Say API is working", "You are a helpful assistant", max_tokens=50)
    
    return JsonResponse({
        'has_api_key': True,
        'api_key_preview': api_key[:20] + '...',
        'response': result if result else 'API call failed',
        'status': 'working' if result else 'failed'
    })


@login_required
def get_user_stats(request):
    user_profile = request.user.profile
    doubts = Doubt.objects.filter(student=request.user)
    
    return JsonResponse({
        'is_paid': user_profile.is_paid,
        'total_doubts': doubts.count(),
        'resolved_doubts': doubts.filter(resolved_at__isnull=False).count(),
        'premium_since': user_profile.updated_at if user_profile.is_paid else None,
    })