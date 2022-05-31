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

from django import forms
from django.core.validators import validate_email
from django.utils.translation import ugettext as _
from django.core.validators import ValidationError

from djangoplicity.contrib.admin.widgets import AdminRichTextAreaWidget


# ======
# Fields
# ======
class MultiEmailField( forms.CharField ):
    """
    Field for entering multiple email addresses (separated by comma).

    Initial code from https://docs.djangoproject.com/en/1.3/ref/forms/validation/#form-field-default-cleaning
    """
    def to_python( self, value ):
        """
        Normalise data to a list of strings.
        """
        # Return an empty list if no input was given.
        if not value:
            return []
        return [x.strip() for x in value.split( ',' )]

    def validate( self, value ):
        """
        Check if value consists only of valid emails.
        """
        super( MultiEmailField, self ).validate( value )

        for email in value:
            validate_email( email )


class EmailListField( forms.CharField ):
    """
    Field for entering multiple email addresses (one per line)
    """
    widget = forms.Textarea( attrs={ 'cols': '60', 'rows': '40' } )

    def to_python( self, value ):
        """
        Normalise the data to a list of strings.
        """
        if not value:
            return []
        return [x.strip() for x in value.split( '\n' )]

    def validate( self, value ):
        """
        Check if value consists only of valid emails.
        """
        super( EmailListField, self ).validate( value )

        for email in value:
            try:
                validate_email( email )
            except ValidationError:
                raise ValidationError( "'%s' is not a valid email address." % email )


# =====
# Forms
# =====
class SendTestMessageForm( forms.Form ):
    """
    Admin form for getting the emails to send the
    test message to.
    """
    emails = MultiEmailField( max_length=255, help_text="Comma-separated list of email addresses" )


class SendMessageForm( forms.Form ):
    """
    Admin form for requesting confirmation to
    send the message.
    """
    send_now = forms.BooleanField()


class RecipientsForm( forms.Form ):
    """
    Admin form for getting the emails to send the
    test message to.
    """
    remove = forms.BooleanField( required=False, label=_( "Remove recipients?" ), help_text=_( "Check-mark this box to remove recipients instead of adding them." ), initial=False )
    recipients = EmailListField( help_text=_( "One email address per line" ) )


class MessageForm(forms.ModelForm):
    html_text = forms.CharField(widget=AdminRichTextAreaWidget({'rows': '30'}), required=False)
