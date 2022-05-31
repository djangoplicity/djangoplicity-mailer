Requirements
============
  * Celery - used for sending messages in the background. 

Installation
============

  * Add ``djangoplicity.mailer'' to INSTALLED_APPS
  * Register admin interface if you are are not using the standard admin site::
  
    import djangoplicity.mailer.admin
    admin_site = AdminSite( ... )
    
    djangoplicity.mailer.admin.register_with_admin( admin_site )
  * Run ``python manage.py migrate mailer'' to create the database tables.    
     