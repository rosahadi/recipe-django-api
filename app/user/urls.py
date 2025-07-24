from django.urls import path
from . import views

app_name = "user"

urlpatterns = [
    path("register/", views.CreateUserView.as_view(), name="register"),
    path("login/", views.login, name="login"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("logout/", views.logout, name="logout"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
]
