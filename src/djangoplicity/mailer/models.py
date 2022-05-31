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

from datetime import datetime

from django.core import mail
from django.db import models
from django.template import defaultfilters
from django.utils.translation import ugettext_lazy as _

from djangoplicity.contacts.models import ContactGroup
from djangoplicity.mailer.tasks import send_message

EMAIL_TYPES = (
    ('P', 'Plain text'),
    ('H', 'HTML'),
)


class Message( models.Model ):
    """
    Email message model. Beside the normal from, subject and body fields, the
    model has a number of extra status fields.
    """

    # Background process have finished the sending of the message to all recipients
    sent = models.BooleanField( default=False, help_text=_("Message has been sent to all recipients.") )

    # Queued for sending means a celery task have been dispatched, and the background worker might be working on sending
    queued = models.BooleanField( default=False, help_text=_("Message is queued for sending.") )

    # Date/time a worker finished sending the message
    delivered = models.DateTimeField( blank=True, null=True, editable=False )

    # Number of successful delivered messages
    messages_delivered = models.PositiveIntegerField( default=0 )

    # Number of failed delivered messages - e.g. SMTP host could not be reached. Has nothing to do with bounces
    messages_failed = models.PositiveIntegerField( default=0, help_text=_( "Failed deliveries" ) )

    # List of Contact groups that should be send the email
    contact_groups = models.ManyToManyField(ContactGroup, help_text=_('Contact groups that will receive the email'), blank=True)

    # HTML or plain text - nothing else supported
    type = models.CharField( max_length=1, choices=EMAIL_TYPES, default='P', help_text=_("For plain-text emails only fill-in the plain text field. For HTML emails, please fill-in both the HTML and the plain-text fields.") )

    from_name = models.CharField( max_length=100, blank=True )
    from_email = models.EmailField( help_text=_( 'Bounced messages will be sent to this email address.' ) )
    reply_to = models.EmailField( verbose_name="Reply-to email", blank=True )
    subject = models.CharField( max_length=255 )
    plain_text = models.TextField( blank=True, help_text=_("Must be filled-in for both plain text and HTML emails. If left blank, it will be generated from the HTML version.") )
    html_text = models.TextField( verbose_name='HTML', blank=True, help_text=_("Must be filled-in for HTML fields.") )

    created = models.DateTimeField( auto_now_add=True )
    last_modified = models.DateTimeField( auto_now=True )

    def get_from( self ):
        """
        Construct the header value for the "from:" email header field.
        """
        return "\"%s\" <%s>" % ( self.from_name, self.from_email ) if self.from_name else self.from_email

    def get_contact_groups_recipients(self):
        '''
        Returns a list of (ContactGroup, Recipients)
        '''
        recipients = []
        for group in self.contact_groups.all():
            recipients.append(
                (group, [c.email for c in group.contact_set.all() if c.email and not c.email.lower().endswith('-invalid')])
            )

        return recipients

    def get_recipients_count( self ):
        """
        Get number of recipients for this email list.
        """
        count = 0
        for _group, recipients in self.get_contact_groups_recipients():
            count += len(recipients)

        return count + Recipient.objects.filter( message=self ).count()
    get_recipients_count.short_description = _( "Recipients" )

    def _send( self, test=True, emails=[] ):
        """
        Send message for real (called by the worker node). Use send_now() or send_test() instead
        of this function. Function is used to send both test emails and the real deal.
        """

        if test:
            recipients = emails
        else:
            recipients = list(self.recipient_set.all().values_list( 'to_email', flat=True ))

            # Add recipients from selected contact groups
            for _group, emails in self.get_contact_groups_recipients():
                recipients += emails

        # Remove duplicates
        recipients = set( [x.lower() for x in recipients] )

        succeeded = 0
        failed = 0

        if len( recipients ) > 0:
            # Open a connection a keep it open until we have sent everything.
            connection = mail.get_connection()

            for r in recipients:
                if self._send_email( connection, r ):
                    succeeded += 1
                else:
                    failed += 1

            # TODO: strange django problem. Throws an exception when
            # closing a conncetion to the mail_debug server.
            try:
                connection.close()
            except Exception:
                pass

        if not test:
            self.messages_delivered = succeeded
            self.messages_failed = failed
            self.delivered = datetime.now()
            self.sent = True
            self.save()

    def _send_email( self, conn, emailaddr ):
        """
        Send this message to a single email address using an already open connection.
        Result is logged to the database.
        """
        msg = None
        if self.is_plaintext():
            # Construct message
            msg = mail.EmailMessage( subject=self.subject, body=self.plain_text, from_email=self.get_from(), to=[emailaddr], connection=conn )
            if self.reply_to:
                msg.headers = { 'Reply-To': self.reply_to }
        elif self.is_html():
            msg = mail.EmailMultiAlternatives( subject=self.subject, body=self.plain_text, from_email=self.get_from(), to=[emailaddr], connection=conn )
            msg.attach_alternative( self.html_text, "text/html" )

        if msg:
            # Construct log message
            log = MessageLog( message=self, recipient=emailaddr )

            # Send the message
            try:
                msg.send( fail_silently=False )
                log.success = True
            except Exception:
                log.success = False

            # Save log
            log.save()
            return log.success
        return False

    def send_now( self ):
        """
        Send message now - message will be queued to be sent via a background worker.
        """
        self.queued = True
        self.save()
        send_message.delay( msg_id=self.pk, test=False )

    def send_test(self, emails):
        """
        Send a test message to the a list of emails - message will be queued to be sent via a background worker.
        """
        send_message.delay( msg_id=self.pk, test=True, emails=emails )

    def save( self, *args, **kwargs ):
        """
        Clear and/or set certain the text/html fields.
        """
        if not self.queued:
            if self.is_plaintext():
                self.html_text = ''
            elif self.is_html():
                if self.plain_text == '' and self.html_text != '':
                    import html2text
                    self.plain_text = html2text.html2text( self.html_text )
                elif self.plain_text != '' and self.html_text == '':
                    self.html_text = defaultfilters.linebreaks( self.plain_text )
        super( Message, self ).save( *args, **kwargs )

    def is_html(self):
        """ Is message an HTML-type message """
        return self.type == 'H'

    def is_plaintext(self):
        """ Is message an plain text-type message """
        return self.type == 'P'

    def __unicode__(self):
        return u"%s (%s)" % ( self.subject, self.pk )

    class Meta:
        ordering = ['-last_modified']


class MessageLog( models.Model ):
    """
    Log for a sent message.
    """
    timestamp = models.DateTimeField( auto_now_add=True, db_index=True )
    message = models.ForeignKey( Message, on_delete=models.CASCADE)
    recipient = models.CharField( max_length=255, db_index=True )
    success = models.BooleanField( default=False, db_index=True )


class Recipient( models.Model ):
    """
    Recipient of a message
    """
    message = models.ForeignKey( Message, on_delete=models.CASCADE)
    to_email = models.CharField( max_length=255 )

    def save( self, *args, **kwargs ):
        self.to_email = self.to_email.lower()
        super( Recipient, self ).save( *args, **kwargs )

    class Meta:
        unique_together = ['message', 'to_email']
