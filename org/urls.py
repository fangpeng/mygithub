from django.conf.urls.defaults import *

urlpatterns = patterns('org',
    (r'^$', 'views.list'),
    (r'^tree/$', 'views.tree'),
    (r'^add/$', 'views.add'),
    (r'^change/(?P<id>\d+)/$', 'views.change'),
    (r'^delete/(?P<id>\d+)/$','views.delete'),
    (r'^save/$','views.save_new'),
    (r'^save/(?P<id>\d+)/$','views.save'),
    (r'^disable/(?P<id>\d+)/$','views.make_disabled'),
    (r'^enable/(?P<id>\d+)/$','views.make_enabled'),
)