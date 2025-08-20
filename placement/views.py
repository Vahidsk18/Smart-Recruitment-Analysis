# placement/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from core.views import is_admin, is_student
from core.models import StudentProfile, User
from .models import Job, Application
from .forms import JobForm, ApplicationStatusForm
from django.db.models import Q # For complex queries
import re # Make sure this is imported

# --- Admin Job Management (remain unchanged) ---
@login_required
@user_passes_test(is_admin)
def job_list_admin(request):
    jobs = Job.objects.all().order_by('-posted_at')
    return render(request, 'placement/admin_job_list.html', {'jobs': jobs})

@login_required
@user_passes_test(is_admin)
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, "Job posted successfully!")
            return redirect('admin_job_list')
        else:
            messages.error(request, "Error posting job.")
    else:
        form = JobForm()
    return render(request, 'placement/job_form.html', {'form': form, 'title': 'Create New Job'})

@login_required
@user_passes_test(is_admin)
def job_update(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully!")
            return redirect('admin_job_list')
        else:
            messages.error(request, "Error updating job.")
    else:
        form = JobForm(instance=job)
    return render(request, 'placement/job_form.html', {'form': form, 'title': 'Update Job'})

@login_required
@user_passes_test(is_admin)
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        job.delete()
        messages.success(request, "Job deleted successfully!")
        return redirect('admin_job_list')
    return render(request, 'placement/job_confirm_delete.html', {'job': job})

# --- Admin Application Management & Filtering ---
@login_required
@user_passes_test(is_admin)
def applications_for_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    applications = Application.objects.filter(job=job).order_by('-applied_at')

    # Filtering Logic (unchanged)
    min_cgpa = request.GET.get('min_cgpa')
    branch = request.GET.get('branch')
    max_backlogs = request.GET.get('max_backlogs')
    skills = request.GET.get('skills')
    status = request.GET.get('status')

    filtered_applications = applications

    if min_cgpa:
        filtered_applications = filtered_applications.filter(student__cgpa__gte=min_cgpa)
    if branch:
        filtered_applications = filtered_applications.filter(student__branch__icontains=branch)
    if max_backlogs:
        filtered_applications = filtered_applications.filter(student__backlogs__lte=max_backlogs)
    if skills:
        for skill_item in skills.split(','):
            filtered_applications = filtered_applications.filter(student__skills__icontains=skill_item.strip())
    if status:
        filtered_applications = filtered_applications.filter(status=status)

    available_branches = StudentProfile.objects.values_list('branch', flat=True).distinct().order_by('branch')
    application_statuses = Application.APPLICATION_STATUS_CHOICES


    context = {
        'job': job,
        'applications': filtered_applications,
        'all_applications_count': applications.count(),
        'available_branches': available_branches,
        'application_statuses': application_statuses,
        'current_min_cgpa': min_cgpa,
        'current_branch': branch,
        'current_max_backlogs': max_backlogs,
        'current_skills': skills,
        'current_status': status,
    }
    return render(request, 'placement/admin_job_applications.html', context)

@login_required
@user_passes_test(is_admin)
def update_application_status(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    if request.method == 'POST':
        form = ApplicationStatusForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, "Application status updated successfully!")
            return redirect('applications_for_job', job_id=application.job.id)
        else:
            # === THIS IS THE LINE THAT WILL SHOW THE ERROR DETAILS ===
            print(f"Form validation errors for application {application_id}: {form.errors}")
            # =======================================================
            messages.error(request, "Error updating application status. Please check inputs and try again.")
    return redirect('applications_for_job', job_id=application.job.id)

# --- Student Job Listing & Application (unchanged) ---
@login_required
@user_passes_test(is_student)
def student_job_list(request):
    jobs = Job.objects.all().order_by('-posted_at')
    student_profile = get_object_or_404(StudentProfile, user=request.user)

    applied_job_ids = student_profile.applications.values_list('job_id', flat=True)

    filtered_jobs = []
    for job in jobs:
        job_eligible = True # Assume eligible by default, then disqualify
        job_eligibility_lower = job.eligibility_criteria.lower()
        student_branch_lower = student_profile.branch.lower()

        # 1. Check Branch Eligibility
        if not ("all branches" in job_eligibility_lower or "any branch" in job_eligibility_lower):
            branch_criteria_found = False
            for b in ["cse", "it", "ece", "eee", "mech", "civil"]: # List common branches
                if b in job_eligibility_lower:
                    branch_criteria_found = True
                    break
            
            if branch_criteria_found: # If specific branches are mentioned
                if student_branch_lower not in job_eligibility_lower:
                    job_eligible = False

        # 2. Check CGPA Eligibility
        if job_eligible and student_profile.cgpa is not None:
            cgpa_match = re.search(r'min(?:imum)?\s+cgpa\s+(\d+\.?\d*)', job_eligibility_lower)
            if cgpa_match:
                try:
                    required_cgpa = float(cgpa_match.group(1))
                    if student_profile.cgpa < required_cgpa:
                        job_eligible = False
                except ValueError:
                    pass
        
        # 3. Check Backlogs Eligibility
        if job_eligible and student_profile.backlogs is not None:
            no_backlogs_match = re.search(r'no\s+backlogs', job_eligibility_lower)
            max_backlogs_match = re.search(r'max(?:imum)?\s+backlogs\s+(\d+)', job_eligibility_lower)

            if no_backlogs_match:
                if student_profile.backlogs > 0:
                    job_eligible = False
            elif max_backlogs_match:
                try:
                    allowed_backlogs = int(max_backlogs_match.group(1))
                    if student_profile.backlogs > allowed_backlogs:
                        job_eligible = False
                except ValueError:
                    pass

        if job_eligible:
            filtered_jobs.append(job)

    context = {
        'jobs': filtered_jobs,
        'student_profile': student_profile,
        'applied_job_ids': list(applied_job_ids),
    }
    return render(request, 'placement/student_job_list.html', context)

@login_required
@user_passes_test(is_student)
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    student_profile = get_object_or_404(StudentProfile, user=request.user)

    if Application.objects.filter(student=student_profile, job=job).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('student_dashboard')

    job_eligible = True # Assume eligible by default for applying
    job_eligibility_lower = job.eligibility_criteria.lower()
    student_branch_lower = student_profile.branch.lower()

    if not ("all branches" in job_eligibility_lower or "any branch" in job_eligibility_lower):
        branch_criteria_found = False
        for b in ["cse", "it", "ece", "eee", "mech", "civil"]: # List common branches
            if b in job_eligibility_lower:
                branch_criteria_found = True
                break
        
        if branch_criteria_found:
            if student_branch_lower not in job_eligibility_lower:
                job_eligible = False

    if job_eligible and student_profile.cgpa is not None:
        cgpa_match = re.search(r'min(?:imum)?\s+cgpa\s+(\d+\.?\d*)', job_eligibility_lower)
        if cgpa_match:
            try:
                required_cgpa = float(cgpa_match.group(1))
                if student_profile.cgpa < required_cgpa:
                    job_eligible = False
            except ValueError:
                pass
    
    if job_eligible and student_profile.backlogs is not None:
        no_backlogs_match = re.search(r'no\s+backlogs', job_eligibility_lower)
        max_backlogs_match = re.search(r'max(?:imum)?\s+backlogs\s+(\d+)', job_eligibility_lower)

        if no_backlogs_match:
            if student_profile.backlogs > 0:
                job_eligible = False
        elif max_backlogs_match:
            try:
                allowed_backlogs = int(max_backlogs_match.group(1))
                if student_profile.backlogs > allowed_backlogs:
                    job_eligible = False
            except ValueError:
                pass

    if not job_eligible:
        messages.error(request, "You do not meet the eligibility criteria for this job.")
        return redirect('student_job_list')

    Application.objects.create(student=student_profile, job=job)
    messages.success(request, f"Successfully applied for {job.job_role} at {job.company_name}!")
    return redirect('student_dashboard')



# review all apliications
@login_required
@user_passes_test(is_admin)
def all_applications_list(request):
    applications = Application.objects.all().order_by('-applied_at')

    context = {
        'applications': applications,
        'job': None, # Set job to None since we are not filtering by job
        'all_applications_count': applications.count(),
        # You would add other filtering options here if needed, similar to applications_for_job
    }
    return render(request, 'placement/admin_job_applications.html', context)








