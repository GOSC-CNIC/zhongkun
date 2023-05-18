from django.shortcuts import render
from django.http.response import HttpResponse
from django.contrib.auth.decorators import login_required

from scripts.workers.report_generator import MonthlyReportNotifier
from report.models import MonthlyReport
from utils.model import OwnerType


@login_required()
def monthly_report_view(request):
    from users.models import UserProfile
    user = UserProfile.objects.filter(username='hai@cnic.cn').first()
    # user = request.user
    mrn = MonthlyReportNotifier()
    report_date = mrn.last_month_1st
    monthly_report = MonthlyReport.objects.filter(
        report_date=report_date, user_id=user.id, owner_type=OwnerType.USER.value).first()
    if monthly_report is None:
        return HttpResponse("""
        <!DOCTYPE html>
        <html>上月月度报表未出</html>
        """.encode(encoding='utf-8'))

    context = mrn.get_context(user=user, report_date=report_date)
    context['monthly_report'] = monthly_report
    return render(request, 'monthly_report.html', context=context)
