# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0002_auto_20150327_1553'),
        ('mailer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='contact_groups',
            field=models.ManyToManyField(to='contacts.ContactGroup'),
            preserve_default=True,
        ),
    ]
