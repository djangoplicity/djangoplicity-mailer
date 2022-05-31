# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_message_contact_groups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='contact_groups',
            field=models.ManyToManyField(help_text='Contact groups that will receive the email', to='contacts.ContactGroup', blank=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='from_email',
            field=models.EmailField(help_text='Bounced messages will be sent to this email address.', max_length=254),
        ),
        migrations.AlterField(
            model_name='message',
            name='reply_to',
            field=models.EmailField(max_length=254, verbose_name=b'Reply-to email', blank=True),
        ),
    ]
