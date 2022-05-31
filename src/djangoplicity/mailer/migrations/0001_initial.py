# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sent', models.BooleanField(default=False, help_text='Message has been sent to all recipients.')),
                ('queued', models.BooleanField(default=False, help_text='Message is queued for sending.')),
                ('delivered', models.DateTimeField(null=True, editable=False, blank=True)),
                ('messages_delivered', models.PositiveIntegerField(default=0)),
                ('messages_failed', models.PositiveIntegerField(default=0, help_text='Failed deliveries')),
                ('type', models.CharField(default=b'P', help_text='For plain-text emails only fill-in the plain text field. For HTML emails, please fill-in both the HTML and the plain-text fields.', max_length=1, choices=[(b'P', b'Plain text'), (b'H', b'HTML')])),
                ('from_name', models.CharField(max_length=100, blank=True)),
                ('from_email', models.EmailField(help_text='Bounced messages will be sent to this email address.', max_length=75)),
                ('reply_to', models.EmailField(max_length=75, verbose_name=b'Reply-to email', blank=True)),
                ('subject', models.CharField(max_length=255)),
                ('plain_text', models.TextField(help_text='Must be filled-in for both plain text and HTML emails. If left blank, it will be generated from the HTML version.', blank=True)),
                ('html_text', models.TextField(help_text='Must be filled-in for HTML fields.', verbose_name=b'HTML', blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-last_modified'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MessageLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('recipient', models.CharField(max_length=255, db_index=True)),
                ('success', models.BooleanField(default=False, db_index=True)),
                ('message', models.ForeignKey(to='mailer.Message')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Recipient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('to_email', models.CharField(max_length=255)),
                ('message', models.ForeignKey(to='mailer.Message')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='recipient',
            unique_together=set([('message', 'to_email')]),
        ),
    ]
