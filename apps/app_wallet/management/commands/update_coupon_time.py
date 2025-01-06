from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.app_wallet.models import CashCoupon, CashCouponActivity


class Command(BaseCommand):
    help = """
        manage.py update_coupon_time --template-id="xx"
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--template-id', default='', dest='template_id', type=str,
            help='The cash coupons of template id.',
        )

    def handle(self, *args, **options):
        template_id = options.get('template_id', '')
        if not template_id:
            raise CommandError("template_id is required.")

        template = CashCouponActivity.objects.filter(id=template_id).first()
        if template is None:
            raise CommandError(f"template(id={template_id}) not found.")

        coupons = CashCoupon.objects.filter(activity_id=template_id)
        coupon_count = coupons.count()

        self.stdout.write(self.style.WARNING(f'template: {template.name}.'))
        self.stdout.write(self.style.WARNING(f'coupon count: {coupon_count}.'))

        if input('Are you sure you want to do this?\n\n' + "Type 'yes' to continue, or 'no' to cancel: ") != 'yes':
            raise CommandError("cancelled.")

        self.update_coupon_effective_time(queryset=coupons)

    def update_coupon_effective_time(self, queryset):
        r = queryset.update(effective_time=timezone.now())

        self.stdout.write(self.style.SUCCESS(f'Successfully update {queryset.count()} coupons effective_time.'))
