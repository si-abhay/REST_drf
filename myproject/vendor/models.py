from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone

class Vendor(models.Model):
    name = models.CharField(max_length=255)
    contact_details = models.TextField()
    address = models.TextField()
    vendor_code = models.CharField(max_length=50, unique=True)
    on_time_delivery_rate = models.FloatField(default=0)
    quality_rating_avg = models.FloatField(default=0)
    average_response_time = models.FloatField(default=0)
    fulfillment_rate = models.FloatField(default=0)

    def update_on_time_delivery_rate(self):
        completed_pos = PurchaseOrder.objects.filter(vendor=self, status='completed')
        on_time_deliveries = completed_pos.filter(delivery_date__lte=timezone.now())
        total_completed_pos = completed_pos.count()
        
        if total_completed_pos > 0:
            self.on_time_delivery_rate = on_time_deliveries.count() / total_completed_pos
            self.save()

    def update_quality_rating_avg(self):
        completed_pos = PurchaseOrder.objects.filter(vendor=self, status='completed', quality_rating__isnull=False)
        if completed_pos.exists():
            self.quality_rating_avg = completed_pos.aggregate(Avg('quality_rating'))['quality_rating__avg']
            self.save()

    def update_average_response_time(self):
        acknowledged_pos = PurchaseOrder.objects.filter(vendor=self, acknowledgment_date__isnull=False)
        if acknowledged_pos.exists():
            response_times = [(po.acknowledgment_date - po.issue_date).total_seconds() for po in acknowledged_pos]
            self.average_response_time = sum(response_times) / len(response_times)
            self.save()

    def update_fulfillment_rate(self):
        completed_pos = PurchaseOrder.objects.filter(vendor=self, status='completed', issue_date__isnull=False)
        successful_fulfillments = completed_pos.exclude(quality_rating__lt=0.5)  # Assuming a quality_rating below 0.5 indicates issues
        total_pos = completed_pos.count()

        if total_pos > 0:
            self.fulfillment_rate = successful_fulfillments.count() / total_pos
            self.save()

class PurchaseOrder(models.Model):
    po_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    order_date = models.DateTimeField()
    delivery_date = models.DateTimeField()
    items = models.JSONField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=50)
    quality_rating = models.FloatField(null=True, blank=True)
    issue_date = models.DateTimeField()
    acknowledgment_date = models.DateTimeField(null=True, blank=True)

class HistoricalPerformance(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    date = models.DateTimeField()
    on_time_delivery_rate = models.FloatField()
    quality_rating_avg = models.FloatField()
    average_response_time = models.FloatField()
    fulfillment_rate = models.FloatField()


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=PurchaseOrder)
def update_vendor_metrics(sender, instance, **kwargs):
    if instance.status == 'completed':
        instance.vendor.update_on_time_delivery_rate()
        instance.vendor.update_quality_rating_avg()

    if instance.acknowledgment_date:
        instance.vendor.update_average_response_time()

    instance.vendor.update_fulfillment_rate()
