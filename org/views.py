#coding=utf-8
import datetime
from django import forms
from urllib import quote
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User, Group
from django.utils.encoding import force_unicode
from auth.decorators import login_required, permission_required
from django.utils.safestring import mark_safe
from models import *
from django.forms.models import modelform_factory
from django.forms import Select
from django.forms.util import ErrorList
from django.contrib import messages
from utils.decorators import handle_error_page

def _add_choice_text(qs):
  map(lambda _:[setattr(_,k[4:-8]+'_text',getattr(_,k)()) or k[4:-8] for k in dir(_) if k.endswith('_display') and k.startswith('get_')],qs)

def _wrap_form(form):
  form.fields['parent'].widget = Select(choices=Org.objects.get_choices())
  return form

@login_required
def list(req):
  org, sub_orgs = req.GET.get('org', None), []
  if org:
    is_top = False
    org = Org.objects.get(pk=org)
    sub_orgs = org.get_children().order_by('sorting_order')
  else:
    is_top = True
    orgs = Org.objects.get_top_list()
    if 1 == len(orgs):
      org = orgs[0]
      sub_orgs = org.get_children().order_by('sorting_order')
    else:
      sub_orgs = orgs
  _add_choice_text(sub_orgs)
  context = {'org': org, 'sub_orgs': sub_orgs, 'is_top':is_top, 'page_title': u'机构列表'}
  context['return_url'] = quote(req.get_full_path())
  return render_to_response('org/list.html', RequestContext(req, dict_=context))

@permission_required('org.manage')
def add(req):
  return_url = req.REQUEST.get('next', '/org/')
  context = {'focus_field': 'code'}
  initial = {}
  parent = req.GET.get('parent', None)
  if parent:
    parent = get_object_or_404(Org, pk=parent)
    initial.update({'parent': parent.id})
    context['page_title'] = u'为 %s 添加下级机构' % parent.name
  else:
    context['page_title'] = u'添加顶级机构'
  f = _wrap_form(modelform_factory(Org)(initial=initial))
  if not parent:
    del f.fields['parent']
  context['form'] = f
  context['return_url'] = quote(return_url)
  return render_to_response('org/add.html', RequestContext(req, dict_=context))

@permission_required('org.manage')
def change(req, id):
  return_url = req.REQUEST.get('next', '/org/')
  context = {'page_title':u'修改机构信息', 'focus_field': 'code',}
  org = get_object_or_404(Org, pk=id)
  f = _wrap_form(modelform_factory(Org)(instance=org))
  context['form'] = f
  context['obj'] = org
  context['return_url'] = quote(return_url)
  return render_to_response('org/change.html', RequestContext(req, dict_=context))

@permission_required('org.manage')
def save(req, id):
  return_url = req.REQUEST.get('next', '/org/')
  context = {'page_title':u'修改机构信息', 'focus_field': 'code'}
  org = get_object_or_404(Org, pk=id)
  f = _wrap_form(modelform_factory(Org)(instance=org, data=req.POST))
  if f.is_valid():
    try:
      obj = f.save()
      messages.info(req, u'%s 保存成功' % obj)
      return HttpResponseRedirect(return_url)
    except Exception, e:
      f.errors['form_self'] = ErrorList([e])
  context['form'] = f
  context['obj'] = org
  context['return_url'] = quote(return_url)
  return render_to_response('org/change.html', RequestContext(req, dict_=context))

@permission_required('org.manage')
def save_new(req):
  return_url = req.REQUEST.get('next', '/org/')
  context = {'focus_field': 'code'}
  parent = req.POST.get('parent', None)
  if parent:
    parent = get_object_or_404(Org, pk=parent)
    context['page_title'] = u'为 %s 添加下级机构' % parent.name
  else:
    context['page_title'] = u'添加顶级机构'
  f = modelform_factory(Org)(data=req.POST.copy())
  if not parent:
    del f.fields['parent']
  if f.is_valid():
    try:
      obj = f.save()
      messages.info(req, u'%s 添加成功' % obj)
      return HttpResponseRedirect(return_url)
    except Exception,e:
      f.errors['form_self'] = ErrorList([e])
  context['form'] = f
  context['return_url'] = quote(return_url)
  return render_to_response('org/add.html', RequestContext(req, dict_=context))

@handle_error_page
@permission_required('org.manage')
def delete(req, id):
  return_url = req.REQUEST.get('next', '/org/')
  context = {'page_title': u'确认删除以下机构'}
  obj = get_object_or_404(Org, pk=id)
  if req.POST.has_key('_has_confirmed'): #经过界面确认
    message = u'%s 删除成功' % obj
    obj.delete()
    messages.info(req, message)
    return HttpResponseRedirect(return_url)
  context['obj'] = obj
  context['objects'] = (obj,)
  context['return_url'] = quote(return_url)
  return render_to_response('org/delete.html', RequestContext(req, dict_=context))

@permission_required('org.query')
def tree(req):
  org = req.GET.get('org', None)
  if org:
    org = get_object_or_404(Org, pk=org)
    orgs = org.get_descendants().order_by('sorting_order')
  else:
    orgs = Org.objects.all().order_by('sorting_order')
  context = {'org': org, 'sub_orgs': orgs}
  context['return_url'] = quote(req.get_full_path())
  return render_to_response('org/tree.html', RequestContext(req, dict_=context))

@handle_error_page
@permission_required('org.manage')
def make_disabled(req, id):
  return_url = req.REQUEST.get('next', '/org/')
  obj = get_object_or_404(Org, pk=id)
  obj.mark_deleted()
  messages.info(req, u'%s 已禁用' % obj)
  return HttpResponseRedirect(return_url)

@handle_error_page
@permission_required('org.manage')
def make_enabled(req, id):
  return_url = req.REQUEST.get('next', '/org/')
  obj = get_object_or_404(Org, pk=id)
  obj.mark_undeleted()
  messages.info(req, u'%s 已启用' % obj)
  return HttpResponseRedirect(return_url)

@permission_required('org.manage')
def reset_debug_data(req):
  from parse import import_from_file
  import os
  from django.conf import settings
  try:
    data_dir = settings.DEBUG_DATA_DIR
  except AttributeError:
    data_dir = './data/'
  path = os.path.abspath(os.path.join(data_dir, "org.txt"))
  ss = [u'用于重置的数据文件是%s' % path]
  try:
    import_from_file(path, reset_table=True)
    for obj in Org.objects.all().order_by('sorting_order'):
      ss.append(u'%s%s' % ('\t' * obj.depth, unicode(obj)))
  except Exception, e:
    ss.append(unicode(e))
  return HttpResponse(u'\r\n'.join(ss))
