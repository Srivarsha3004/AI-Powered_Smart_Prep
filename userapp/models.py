from django.db import models

# Create your models here.
class User(models.Model):
    full_name = models.CharField(max_length=100, verbose_name="User Name")
    email = models.EmailField(verbose_name="Email")
    password = models.CharField(max_length=128, verbose_name="Password")
    phone_number = models.CharField(max_length=15, verbose_name="Phone Number")
    age =models.CharField(max_length=15, verbose_name="age")
    address = models.TextField(verbose_name="Address")
    photo = models.ImageField(upload_to='profiles/', verbose_name="Upload Profile", null=True, blank=True)
    otp = models.CharField(max_length=6, default='000000', help_text='Enter OTP for verification')
    otp_status = models.CharField(max_length=15, default='Not Verified', help_text='OTP status')
    status = models.CharField(max_length=15,default='Accepted')

    def __str__(self):
        return self.full_name


class Conversation(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"User: {self.user_message[:50]}..."

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=255)
    user_email = models.EmailField()
    rating = models.IntegerField()
    additional_comments = models.TextField()
    sentiment = models.CharField(max_length=20, null=True)  # Add this field to store the sentiment
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback'