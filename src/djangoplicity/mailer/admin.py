# -*- coding: utf-8 -*-
#
# djangoplicity-mailer
# Copyright (c) 2007-2011, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the European Southern Observatory nor the names
#      of its contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY ESO ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL ESO BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE
#

"""
Administration inteface for djangoplicity-mailer. Five extra views are
defined for a message:

 * html - the HTML content of a message (can be included via iframe)
 * text - the text content of the message (can be included via iframe)
 * send_test - send a test of the message.
 * send_now - send the message now.
 * import - import/remove a list of recipients
"""

from django.conf.urls import url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _
from djangoplicity.mailer.forms import MessageForm
from djangoplicity.mailer.models import Message, MessageLog, Recipient


class MessageAdmin( admin.ModelAdmin ):
    list_display = [ 'subject', 'from_name', 'from_email', 'type', 'queued', 'sent', 'delivered', 'messages_delivered', 'messages_failed' ]
    list_filter = ['type', 'sent', 'delivered', 'created', 'last_modified']

    search_fields = ['from_name', 'from_email', 'reply_to', 'subject', 'plain_text', 'html_text']
    readonly_fields = ['queued', 'sent', 'delivered', 'created', 'last_modified', 'messages_delivered', 'messages_failed', 'get_recipients_count']
    filter_horizontal = ['contact_groups']

    fieldsets = (
        (
            None,
            {
                'fields': ( 'queued', 'sent', 'delivered', 'get_recipients_count',),
            }
        ),
        (
            "Sender",
            {
                'fields': ( 'from_name', 'from_email', 'reply_to' ),
            }
        ),
        (
            "Recipients Contact Groups",
            {
                'fields': ( 'contact_groups', ),
            }
        ),
        (
            "Content",
            {
                'fields': ( 'type', 'subject', 'plain_text', 'html_text' ),
            }
        ),
        (
            "Status",
            {
                'fields': ( 'messages_delivered', 'messages_failed', 'created', 'last_modified', ),
            }
        ),
    )
    form = MessageForm

    def get_urls( self ):
        urls = super( MessageAdmin, self ).get_urls()
        extra_urls = [
            url(r'^(?P<pk>[0-9]+)/html/$', self.admin_site.admin_view(self.html_view), name='mailer_html'),
            url(r'^(?P<pk>[0-9]+)/text/$', self.admin_site.admin_view(self.text_view), name='mailer_text'),
            url(r'^(?P<pk>[0-9]+)/send_test/$', self.admin_site.admin_view(self.send_test_view), name='mailer_send_test'),
            url(r'^(?P<pk>[0-9]+)/send_now/$', self.admin_site.admin_view(self.send_now_view), name='mailer_send_now'),
            url(r'^(?P<pk>[0-9]+)/import/$', self.admin_site.admin_view(self.import_view), name='mailer_import'),
        ]
        return extra_urls + urls

    def html_view( self, request, pk=None ):
        """
        View HTML version of message
        """
        msg = get_object_or_404( Message, pk=pk )

        if not msg.is_html():
            raise Http404

        return HttpResponse( msg.html_text, content_type="text/html" )

    def text_view( self, request, pk=None ):
        """
        View text version of message
        """
        msg = get_object_or_404( Message, pk=pk )
        response = HttpResponse( msg.plain_text )
        response["Content-Type"] = "text/plain; charset=utf-8"
        return response

    def send_test_view( self, request, pk=None ):
        """
        Send test of a message
        """
        from djangoplicity.mailer.forms import SendTestMessageForm

        msg = get_object_or_404( Message, pk=pk )

        if request.method == "POST":
            form = SendTestMessageForm( request.POST )
            if form.is_valid():
                emails = form.cleaned_data['emails']
                msg.send_test( emails )
                self.message_user( request, _( "Test message have been added to the send queue (will be sent to %(emails)s)" ) % { 'emails': ", ".join( emails ) } )
                return HttpResponseRedirect( reverse( "%s:mailer_message_change" % self.admin_site.name, args=[msg.pk] ) )
        else:
            form = SendTestMessageForm()

        ctx = {
            'title': _( '%s: Send test email' ) % force_unicode( self.model._meta.verbose_name ).title(),
            'adminform': form,
            'original': msg,
        }

        return self._render_admin_view( request, "admin/mailer/message/send_test_form.html", ctx )

    def send_now_view( self, request, pk=None ):
        """
        Send a message.
        """
        from djangoplicity.mailer.forms import SendMessageForm

        msg = get_object_or_404( Message, pk=pk )

        if request.method == "POST":
            # Don't allow to sent a message more than once.
            if msg.sent or msg.queued:
                raise Http404

            form = SendMessageForm( request.POST )
            if form.is_valid():
                send_now = form.cleaned_data['send_now']
                if send_now:
                    msg.send_now()
                    self.message_user( request, _( "Message %s has been added to the send queue" % msg.pk ) )
                    return HttpResponseRedirect( reverse( "%s:mailer_message_change" % self.admin_site.name, args=[msg.pk] ) )

            if 'send_now' not in form.errors:
                form.errors['send_now'] = []
            form.errors['send_now'].append( "Please check-mark the box to send the message." )
        else:
            form = SendMessageForm()

        ctx = {
            'title': _( '%s: Send now' ) % force_unicode( self.model._meta.verbose_name ).title(),
            'adminform': form,
            'original': msg,
            'groups': msg.get_contact_groups_recipients(),
        }

        return self._render_admin_view( request, "admin/mailer/message/send_now_form.html", ctx )

    def import_view( self, request, pk=None ):
        """
        Import list of recipients
        """
        from djangoplicity.mailer.forms import RecipientsForm

        msg = get_object_or_404( Message, pk=pk )

        if request.method == "POST":
            form = RecipientsForm( request.POST )
            if form.is_valid():
                emails = form.cleaned_data['recipients']
                remove = form.cleaned_data['remove']

                failed = 0
                success = 0

                for e in emails:
                    try:
                        if remove:
                            Recipient.objects.get( to_email=e, message=msg ).delete()
                        else:
                            obj = Recipient( to_email=e, message=msg )
                            obj.save()
                        success += 1
                    except (IntegrityError, Recipient.DoesNotExist):
                        failed += 1

                if remove:
                    self.message_user( request, _( "Recipients removed (%s removed, %s did not exist)." ) % ( success, failed ) )
                else:
                    self.message_user( request, _( "Recipients imported (%s new, %s already existed)." ) % ( success, failed ) )

                return HttpResponseRedirect( reverse( "%s:mailer_message_change" % self.admin_site.name, args=[msg.pk] ) )
        else:
            form = RecipientsForm()

        ctx = {
            'title': _( 'Recipients import' ),
            'adminform': form,
            'original': msg,
        }

        return self._render_admin_view( request, "admin/mailer/message/import_form.html", ctx )

    def _render_admin_view( self, request, template, context ):
        """
        Helper function for rendering an admin view
        """
        opts = self.model._meta

        defaults = {
            'app_label': opts.app_label,
            'opts': opts,
        }
        defaults.update(context)

        return render(request, template, defaults)


class MessageLogAdmin( admin.ModelAdmin ):
    list_display = [ 'timestamp', 'message', 'recipient', 'success', ]
    list_filter = [ 'timestamp', 'success', ]
    search_fields = ['message__subject', 'recipient', ]
    readonly_fields = ['timestamp', 'message', 'recipient', 'success', ]

    def has_add_permission( self, request ):
        return False

    def has_change_permission( self, request, obj=None ):
        return True

    def has_delete_permission( self, request, obj=None ):
        return False


class RecipientAdmin( admin.ModelAdmin ):
    list_display = [ 'to_email', 'message', ]
    search_fields = ['to_email', 'message__subject', ]

    def has_add_permission( self, request ):
        return False


def register_with_admin( admin_site ):
    admin_site.register( Message, MessageAdmin )
    admin_site.register( MessageLog, MessageLogAdmin )
    admin_site.register( Recipient, RecipientAdmin )
