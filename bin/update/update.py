"""
Deploy this project in dev/stage/production.

Requires commander_ which is installed on the systems that need it.

.. _commander: https://github.com/oremj/commander
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import task, hostgroups
import commander_settings as settings


@task
def update_code(ctx, tag):
    """Update the code to a specific git reference (tag/sha/etc)."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('git checkout %s' % tag)
        ctx.local('git pull -f')
        ctx.local("find . -type f -name '*.pyc' -delete")
        ctx.local('virtualenv ../venv')
        ctx.local('../venv/bin/pip install bin/peep-2.1.1.tar.gz')
        ctx.local('../venv/bin/peep install -r requirements.txt')
        ctx.local('virtualenv --relocatable ../venv')


@task
def update_assets(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local("../venv/bin/python manage.py collectstatic --noinput")


@task
def update_db(ctx):
    """Update the database schema, if necessary."""

    with ctx.lcd(settings.SRC_DIR):
        ctx.local('../venv/bin/python manage.py syncdb')
        ctx.local('../venv/bin/python manage.py migrate --delete-ghost-migrations --noinput airmozilla.main')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.comments')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.uploads')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.subtitles')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.search')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.surveys')
        ctx.local('../venv/bin/python manage.py migrate airmozilla.cronlogger')


@task
def install_cron(ctx):
    """Use gen-crons.py method to install new crontab."""

    with ctx.lcd(settings.SRC_DIR):
        ctx.local('../venv/bin/python ./bin/crontab/gen-crons.py -p ../venv/bin/python -w %s -u apache > /etc/cron.d/%s_generated' % (settings.SRC_DIR, settings.REMOTE_HOSTNAME))


@task
def checkin_changes(ctx):
    """Use the local, IT-written deploy script to check in changes."""
    ctx.local(settings.DEPLOY_SCRIPT)


@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_app(ctx):
    """Call the remote update script to push changes to webheads."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/etc/init.d/httpd graceful')


@hostgroups(settings.CELERY_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def update_celery(ctx):
    """Update and restart Celery."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/sbin/service %s restart' % settings.CELERY_SERVICE)


@task
def update_info(ctx):
    """Write info about the current state to a publicly visible file."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('date')
        ctx.local('git branch')
        ctx.local('git log -3')
        ctx.local('git status')
        ctx.local('git submodule status')

        ctx.local('git rev-parse HEAD > media/revision')


@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    """Update code to pick up changes to this file."""
    update_code(ref)


@task
def update(ctx):
    update_assets()
    update_db()


@task
def deploy(ctx):
    install_cron()
    checkin_changes()
    deploy_app()
    #update_celery()
    update_info()


@task
def update_site(ctx, tag):
    """Update the app to prep for deployment."""
    pre_update(tag)
    update()
