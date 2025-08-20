# core/views.py

import os
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import StudentSignUpForm, AdminSignUpForm, LoginForm, StudentProfileForm
from .models import StudentProfile, User
from placement.models import Job, Application # Ensure Job model is imported
from django.db.models import Q # For complex queries
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.messages import get_messages 
from placement.models import Job, Application # Ensure Job model is imported
from django.db.models import Q, Count 

# --- Helper Functions (unchanged) ---
def is_student(user):
    return user.is_authenticated and user.user_type == 'student'

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

# --- Authentication Views (unchanged) ---
def student_signup(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Student account created successfully!")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Error creating student account.")
    else:
        form = StudentSignUpForm()
    return render(request, 'core/student_signup.html', {'form': form})

def admin_signup(request):
    if request.method == 'POST':
        form = AdminSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Admin account created successfully! You are now logged in.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Error creating admin account.")
    else:
        form = AdminSignUpForm()
    return render(request, 'core/admin_signup.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                if user.user_type == 'admin':
                    return redirect('admin_dashboard')
                elif user.user_type == 'student':
                    return redirect('student_dashboard')
                else:
                    messages.error(request, "Unknown user type. Please contact support.")
                    logout(request)
                    return redirect('login')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def user_logout(request):
    # Clear all previous messages
    storage = get_messages(request)
    for _ in storage:
        pass  # consume and clear old messages

    # Now log out
    logout(request)

    # Add only logout message
    messages.success(request, "You have been logged out.")
    return redirect("login")

# --- Dashboards ---
@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    applications = student_profile.applications.all().order_by('-applied_at')

    # Fetch recent jobs (e.g., last 5, similar to admin dashboard)
    # This job list will NOT be filtered by student eligibility here; it's just recent posts.
    # The full filtered list is on /student/jobs/
    recent_jobs = Job.objects.all().order_by('-posted_at')[:5]

    context = {
        'student_profile': student_profile,
        'applications': applications,
        'recent_jobs': recent_jobs, # <--- ADDED: Pass recent jobs to context
    }
    return render(request, 'core/student_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_students = StudentProfile.objects.count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()
    
    total_coordinators = User.objects.filter(user_type='admin').count()
    pending_coordinators_approval = 0 # Placeholder for future expansion
    pending_students_confirmation = StudentProfile.objects.filter(
        Q(applications__isnull=True) | Q(cgpa__isnull=True) | Q(skills__isnull=True)
    ).distinct().count()

    # New code to get top job application trends
    top_job_trends = Job.objects.annotate(application_count=Count('applications')).order_by('-application_count')[:5]

    recent_applications = Application.objects.filter(status='applied').order_by('-applied_at')[:10]

    context = {
        'total_students': total_students,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'total_coordinators': total_coordinators,
        'pending_coordinators_approval': pending_coordinators_approval,
        'pending_students_confirmation': pending_students_confirmation,
        'top_job_trends': top_job_trends, # <--- ADDED: Pass top job trends to context
        'recent_applications': recent_applications,
    }
    return render(request, 'core/admin_dashboard.html', context)

# --- Admin Student List View (unchanged) ---
@login_required
@user_passes_test(is_admin)
def student_list_admin(request):
    all_students = StudentProfile.objects.all().order_by('roll_number')

    search_query = request.GET.get('q')
    branch_filter = request.GET.get('branch')
    min_cgpa = request.GET.get('min_cgpa')
    max_backlogs = request.GET.get('max_backlogs')
    
    filtered_students = all_students

    if search_query:
        filtered_students = filtered_students.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(roll_number__icontains=search_query)
        )
    if branch_filter:
        filtered_students = filtered_students.filter(branch__icontains=branch_filter)
    if min_cgpa:
        filtered_students = filtered_students.filter(cgpa__gte=min_cgpa)
    if max_backlogs:
        filtered_students = filtered_students.filter(backlogs__lte=max_backlogs)

    available_branches = StudentProfile.objects.values_list('branch', flat=True).distinct().order_by('branch')

    context = {
        'students': filtered_students,
        'available_branches': available_branches,
        'all_students_count': all_students.count(),
        'current_search_query': search_query,
        'current_branch_filter': branch_filter,
        'current_min_cgpa': min_cgpa,
        'current_max_backlogs': max_backlogs,
    }
    return render(request, 'core/student_list_admin.html', context)

# --- Student Profile Management (unchanged) ---
@login_required
@user_passes_test(is_student)
def student_profile_view(request):
    student_profile, created = StudentProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student_profile)
        if form.is_valid():
            form.save()
            if 'resume_file' in request.FILES:
                parse_resume_for_student(student_profile)
            messages.success(request, "Profile updated successfully!")
            return redirect('student_profile_view')
        else:
            messages.error(request, "Error updating profile.")
    else:
        form = StudentProfileForm(instance=student_profile)
    return render(request, 'core/student_profile.html', {'form': form, 'student_profile': student_profile})

# --- ML/NLP (Resume Parsing) Integration (unchanged) ---
import spacy
from docx import Document
import PyPDF2


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
    nlp = None


def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def extract_text_from_docx(docx_path):
    text = ""
    try:
        doc = Document(docx_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
    return text

def parse_resume_text(text):
    if not nlp:
        return {'skills': '', 'education': '', 'experience': '', 'phone_number': ''}

    doc = nlp(text)
    
    skills = []
    education = []
    experience = []
    phone_number = ""
    
    common_skills = ["python", "java", "django", "react", "sql", "data analysis", "machine learning", "web development", "javascript", "html", "css", "c++", "aws", "git"]
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            skills.append(skill.capitalize())

    for ent in doc.ents:
        if ent.label_ == "ORG" and ("university" in ent.text.lower() or "college" in ent.text.lower()):
            education.append(ent.text)
        elif ent.label_ == "ORG" and re.search(r'\b(b\.?tech|m\.?tech|bachelor|master|ph\.?d)\b', ent.text, re.IGNORECASE):
             education.append(ent.text)

    for sent in doc.sents:
        if "experience" in sent.text.lower() or "worked at" in sent.text.lower() or "software engineer" in sent.text.lower():
            experience.append(sent.text)

    phone_match = re.search(r'\b(?:\+91[\s-]?)?[6789]\d{9}\b', text)
    if not phone_match:
        phone_match = re.search(r'\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b', text)

    if phone_match:
        phone_number = phone_match.group(0)


    parsed_data = {
        'skills': ", ".join(list(set(skills))),
        'education': "\n".join(list(set(education))),
        'experience': "\n".join(list(set(experience))),
        'phone_number': phone_number,
    }
    return parsed_data

def parse_resume_for_student(student_profile):
    if student_profile.resume_file:
        file_path = student_profile.resume_file.path
        file_extension = os.path.splitext(file_path)[1].lower()
        
        extracted_text = ""
        if file_extension == '.pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            extracted_text = extract_text_from_docx(file_path)
        else:
            messages.error(f"Unsupported file type: {file_extension}. Only PDF and DOCX are supported.")
            return

        parsed_data = parse_resume_text(extracted_text)
        
        student_profile.skills = parsed_data.get('skills', student_profile.skills)
        student_profile.education = parsed_data.get('education', student_profile.education)
        student_profile.experience = parsed_data.get('experience', student_profile.experience)
        student_profile.phone_number = parsed_data.get('phone_number', student_profile.phone_number)
        
        student_profile.save()
        print(f"Resume parsed and profile updated for {student_profile.user.username}")
    else:
        print(f"No resume file found for {student_profile.user.username}")



# //////////////
@login_required
@user_passes_test(is_admin)
def all_applications_admin(request):
    """
    View to list all student applications, with optional job filter.
    """
    jobs = Job.objects.all().order_by('-posted_at')  # for filter dropdown
    job_id = request.GET.get('job_id')

    applications = Application.objects.select_related('student__user', 'job').order_by('-applied_at')

    # Apply filter if job_id is provided
    selected_job = None
    if job_id:
        selected_job = get_object_or_404(Job, id=job_id)
        applications = applications.filter(job=selected_job)

    context = {
        'applications': applications,
        'all_applications_count': applications.count(),
        'jobs': jobs,
        'selected_job': selected_job,
    }
    return render(request, 'core/all_applications_admin.html', context)
