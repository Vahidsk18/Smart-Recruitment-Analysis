# placement/models.py

from django.db import models
from core.models import User, StudentProfile # Import your custom User and StudentProfile

class Job(models.Model):
    company_name = models.CharField(max_length=100)
    job_role = models.CharField(max_length=100)
    description = models.TextField()
    salary_package = models.CharField(max_length=50, blank=True, null=True)
    eligibility_criteria = models.TextField(help_text="e.g., Min CGPA 7.0, CSE/IT branches, No backlogs")
    application_deadline = models.DateField()
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_jobs')
    posted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_role} at {self.company_name}"

class Application(models.Model):
    APPLICATION_STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS_CHOICES, default='applied')
    admin_comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'job') # A student can apply for a job only once

    def __str__(self):
        return f"{self.student.user.username} applied for {self.job.job_role} at {self.job.company_name} - Status: {self.status}"