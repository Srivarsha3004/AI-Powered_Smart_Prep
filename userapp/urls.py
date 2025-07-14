from django.contrib import admin
from django.urls import path,include
from userapp import views as views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('about/',views.about,name='about'),
    # path('admin/login/',views.admin,name='admin'),
    path('contact/',views.contact,name='contact'),
    path('register/',views.user_register,name='user_register'),
    # path('resend/otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.user_login, name='user_login'),
    path('otp/', views.user_otp, name='user_otp'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path("logout/",views.user_logout,name="user_logout"),



    path("pdf/",views.pdf,name="pdf"),
    # path("text/",views.text,name="text"),
    path("profile/", views.user_profile,name="user_profile"),
    path('feedback/', views.feedback, name='feedback'),
    path('chatbot/', views.user_chatbot, name='chatbot'),








      
                   
]