from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.core.mail import send_mail

'''Number of jury members to send emails to'''
N_USERS = 5


class DataScienceResource(models.Model):
    '''Each instance represents a dataset or method
    used by the Nesta data science team. The creation of a
    new object will lead to :obj:`N_USERS` members being emailed.
    The added bonus is that this is (of course) the Django ORM,
    so all of our data sources and methods are hand-audited in
    this way.
    '''
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(verbose_name=("Description "
                                                 "and justification"))
    resource_type = models.CharField(
        max_length=6,
        choices=(('DATA', 'Data'), ('METHOD', 'Method')),
        default='DATA',
    )
    github_repo = models.CharField(max_length=200, blank=True)
    data_source = models.CharField(max_length=200)
    data_location = models.CharField(max_length=400)
    creation_date = models.DateTimeField('Date created', auto_now_add=True,
                                         blank=True, editable=False)
    active = models.BooleanField(default=True)
    approved = models.BooleanField(default=False, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        '''Save the object and email jury members'''
        super().save(*args, **kwargs)

        # Get the users, excluding the submitter
        users = User.objects.exclude(pk=self.user.pk).order_by('?').all()
        n_users = len(users)
        if n_users < N_USERS:
            n_users = N_USERS

        # Email all users
        sub = ('Ethics panel: new data science {} ({}) await approval.')
        msg = ('Dear {},<br><br>Please click '
               '<a href="http://127.0.0.1:8000/jury/{}">here to review</a>')
        for user in users[:n_users]:
            send_mail(sub.format(self.resource_type, self.title),
                      msg.format(user.username, self.title),
                      "Nesta Data Science Ethics",
                      [user.email],
                      fail_silently=False)
            # Create a Decisions object for each member of the jury
            d, created = Decisions.objects.get_or_create(user=user,
                                                         resource=self)
            if created:
                d.save(first_time=True)


class Decisions(models.Model):
    '''Instances represent the individual decision of a
    jury member (characterised by :obj:`user`) on
    :obj:`DataScienceResource` :obj:`resource`'''
    comment = models.TextField(default=("Please enter a comment or "
                                        "reason for deferment."),
                               editable=False)
    decision = models.BooleanField(default=False, editable=False)
    creation_date = models.DateTimeField('Date created', auto_now_add=True,
                                         blank=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    resource = models.ForeignKey(DataScienceResource,
                                 on_delete=models.CASCADE)

    class Meta:
        '''Specify a pseudo primary/unique key as a combination.
        The implication here is that each user can only adjudicate
        on a resource once.'''
        unique_together = (("resource", "user"),)
        verbose_name_plural = "Decisions"

    def __unicode__(self):
        return "Decision on {} by {}".format(self.resource.title,
                                             self.user.username)

    def __str__(self):
        return "Decision on {} by {}".format(self.resource.title,
                                             self.user.username)

    def save(self, *args, **kwargs):
        '''Save the :obj:`Decision`, and update the
        :obj:`DataScienceResource` if required.'''
        # Update the DataScienceResource if required
        if "first_time" not in kwargs:
            # Sum up the number of accepts
            decisions = Decisions.objects.filter(resource=self.resource).all()
            n_accepts = sum(d.decision for d in decisions)
            # If the maximum number of accepts has been reached, then
            # approve this DataScienceResource
            if n_accepts == len(decisions):
                dsr = DataScienceResource.objects.filter(pk=self.resource.pk)
                dsr.update(approved=True, active=False)
        else:
            kwargs.pop("first_time")
        super().save(*args, **kwargs)
