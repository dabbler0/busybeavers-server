from django.urls import path

from . import views

urlpatterns = [
        path('verify/', views.verify, name='verify'),
        path('approve-by-discord/', views.approve_by_discord, name='approve-by-discord'),
        path('request/', views.request, name='request'),
        path('get-outstanding/', views.get_approvals, name='get-outstanding'),
        path('confirm/', views.confirm, name='confirm'),
        path('whois-id/', views.whois_by_id, name='whois-by-id'),
        path('register-preapproved/', views.register_preapproved, name='register-preapproved'),
        path('replace-kerberos/', views.replace_kerberos, name='replace-kerberos'),
        path('count/', views.how_many_kerbs, name='count')
]
