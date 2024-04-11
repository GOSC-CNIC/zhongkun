from django.http.response import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import loader

from .workers.report_generator import MonthlyReportNotifier, get_report_period_start_and_end
from report.models import MonthlyReport
from utils.model import OwnerType


@login_required()
def monthly_report_view(request):
    user = request.user
    start, end = get_report_period_start_and_end()
    mrn = MonthlyReportNotifier(report_data=end)
    report_date = mrn.report_period_date
    monthly_report = MonthlyReport.objects.filter(
        report_date=report_date, user_id=user.id, owner_type=OwnerType.USER.value).first()
    if monthly_report is None:
        return HttpResponse("""
        <!DOCTYPE html>
        <html>上月月度报表未出</html>
        """.encode(encoding='utf-8'))

    context = mrn.get_context(user=user, report_date=report_date)
    context['monthly_report'] = monthly_report
    content = loader.render_to_string('monthly_report.html', context=context, request=request, using=None)
    content = mrn.html_minify(content)
    return HttpResponse(content)
